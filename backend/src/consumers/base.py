"""
Kafka consumer base class.

Provides async consumer with error handling and graceful shutdown.
"""

import asyncio
import json
from typing import Optional, Callable, Any, List
from abc import ABC, abstractmethod

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class BaseKafkaConsumer(ABC):
    """
    Base class for Kafka consumers.
    
    Handles:
    - Async message consumption
    - Deserialization
    - Error handling with retries
    - Graceful shutdown
    """
    
    def __init__(
        self,
        topics: List[str],
        group_id: Optional[str] = None,
        auto_offset_reset: str = "latest",
    ):
        """
        Initialize consumer.
        
        Args:
            topics: List of Kafka topics to subscribe to
            group_id: Consumer group ID (defaults to settings)
            auto_offset_reset: Where to start consuming (earliest/latest)
        """
        self.topics = topics
        self.group_id = group_id or settings.kafka_consumer_group
        self.auto_offset_reset = auto_offset_reset
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> asyncio.Task:
        """Start the consumer in background."""
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info(
            "Kafka consumer started",
            consumer=self.__class__.__name__,
            topics=self.topics,
            group_id=self.group_id
        )
        return self._task
    
    async def stop(self):
        """Stop the consumer gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.consumer:
            await self.consumer.stop()
        
        logger.info("Kafka consumer stopped", consumer=self.__class__.__name__)
    
    async def _consume_loop(self):
        """Main consumption loop."""
        # Create consumer
        self.consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
        )
        
        try:
            await self.consumer.start()
            logger.info("Consumer connected to Kafka", topics=self.topics)
            
            async for message in self.consumer:
                if not self._running:
                    break
                
                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(
                        "Error processing message",
                        error=str(e),
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                    )
                    # Continue processing next message
        
        except KafkaError as e:
            logger.error("Kafka error in consumer loop", error=str(e))
            raise
        
        finally:
            await self.consumer.stop()
    
    async def _process_message(self, message):
        """
        Process a single message.
        
        Deserializes and calls the subclass handler.
        """
        try:
            # Log message received
            logger.debug(
                "Message received",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )
            
            # Call subclass handler
            await self.handle_message(
                topic=message.topic,
                key=message.key.decode('utf-8') if message.key else None,
                value=message.value,
                timestamp=message.timestamp,
            )
        
        except Exception as e:
            logger.error(
                "Handler error",
                error=str(e),
                topic=message.topic,
            )
            raise
    
    @abstractmethod
    async def handle_message(
        self,
        topic: str,
        key: Optional[str],
        value: dict,
        timestamp: int,
    ):
        """
        Handle a message from Kafka.
        
        Must be implemented by subclasses.
        
        Args:
            topic: Topic name
            key: Message key (usually ID)
            value: Deserialized message value (dict)
            timestamp: Message timestamp (ms)
        """
        pass
