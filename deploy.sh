#!/bin/bash
# ===========================================
# FleetFlow - Production Deployment Script
# ===========================================

set -e

echo "🚀 FleetFlow Production Deployment"
echo "===================================="

# Check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    echo "✅ Prerequisites met"
}

# Check environment files
check_env_files() {
    echo "📋 Checking environment files..."
    
    if [ ! -f "backend/.env" ]; then
        echo "⚠️  backend/.env not found"
        echo "   Copying from .env.example..."
        cp backend/.env.example backend/.env
        echo "   ⚠️  IMPORTANT: Edit backend/.env with production values!"
    fi
    
    if [ ! -f "frontend/.env.local" ]; then
        echo "⚠️  frontend/.env.local not found"
        echo "   Copying from .env.example..."
        cp frontend/.env.example frontend/.env.local
        echo "   ⚠️  IMPORTANT: Edit frontend/.env.local with production values!"
    fi
    
    echo "✅ Environment files ready"
}

# Build images
build_images() {
    echo "🔨 Building Docker images..."
    
    docker-compose build --no-cache
    
    echo "✅ Images built successfully"
}

# Start services
start_services() {
    echo "🚀 Starting services..."
    
    docker-compose up -d
    
    echo "✅ Services started"
}

# Health check
health_check() {
    echo "🏥 Running health checks..."
    
    sleep 10  # Wait for services to start
    
    # Check backend
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ Backend API: healthy"
    else
        echo "⚠️  Backend API: not responding"
    fi
    
    # Check frontend
    if curl -s http://localhost:3000 > /dev/null; then
        echo "✅ Frontend: healthy"
    else
        echo "⚠️  Frontend: not responding"
    fi
    
    # Check metrics
    if curl -s http://localhost:8000/metrics > /dev/null; then
        echo "✅ Metrics: available"
    else
        echo "⚠️  Metrics: not available"
    fi
}

# Print status
print_status() {
    echo ""
    echo "===================================="
    echo "🎉 FleetFlow Deployment Complete!"
    echo "===================================="
    echo ""
    echo "Access Points:"
    echo "  📱 Frontend:    http://localhost:3000"
    echo "  🔌 API:         http://localhost:8000"
    echo "  📊 API Docs:    http://localhost:8000/docs"
    echo "  📈 Metrics:     http://localhost:8000/metrics"
    echo "  🔍 GraphQL:     http://localhost:8000/graphql"
    echo "  🌐 WebSocket:   ws://localhost:8002"
    echo ""
    echo "Monitoring:"
    echo "  📊 Prometheus:  http://localhost:9090"
    echo "  📈 Grafana:     http://localhost:3001 (admin/admin)"
    echo ""
    echo "Commands:"
    echo "  View logs:      docker-compose logs -f"
    echo "  Stop:           docker-compose down"
    echo "  Restart:        docker-compose restart"
    echo ""
}

# Main
main() {
    check_prerequisites
    check_env_files
    build_images
    start_services
    health_check
    print_status
}

main "$@"
