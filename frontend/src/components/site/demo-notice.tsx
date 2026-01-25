"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, Github } from "lucide-react";

export function DemoNotice() {
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let active = true;

    const checkHealth = async () => {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        if (!res.ok) {
          throw new Error("health check failed");
        }
        const data = await res.json().catch(() => ({}));
        if (active) {
          setIsLive(data?.status ? data.status !== "unhealthy" : true);
        }
      } catch {
        if (active) {
          setIsLive(false);
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div
      className={`bg-gradient-to-r ${
        isLive
          ? "from-emerald-900/40 via-emerald-800/30 to-emerald-900/40 border-emerald-500/40"
          : "from-amber-900/30 via-stone-900/40 to-amber-900/20 border-amber-500/40"
      } border rounded-2xl p-5`}
    >
      <div className="flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl ${
              isLive ? "bg-emerald-500/20" : "bg-amber-500/20"
            } flex items-center justify-center`}
          >
            {isLive ? (
              <span className="h-3 w-3 rounded-full bg-emerald-400 animate-pulse" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            )}
          </div>
          <div>
            <h3 className={`${isLive ? "text-emerald-200" : "text-amber-200"} font-bold`}>
              {isLive ? "Live Data" : "Demo Mode"}
            </h3>
            <p className={`${isLive ? "text-emerald-300/70" : "text-amber-300/70"} text-xs`}>
              {isLive ? "Connected to FleetFlow API - real-time updates" : "Free-tier demo with limited workloads"}
            </p>
          </div>
        </div>

        <div className="flex-1 md:text-center">
          <p className={`${isLive ? "text-emerald-100/80" : "text-amber-100/80"} text-sm`}>
            {isLive ? (
              <>
                Streaming routes via{" "}
                <span className="text-emerald-300 font-semibold">Kafka + WebSocket</span>
              </>
            ) : (
              <>
                Run locally for{" "}
                <span className="text-amber-300 font-semibold">Kafka, Flink, Airflow, PostGIS</span>
              </>
            )}
          </p>
        </div>

        <a
          href="https://github.com/HuLaxx/FleetFlow"
          target="_blank"
          rel="noopener noreferrer"
          className={`inline-flex items-center gap-2 px-4 py-2.5 ${
            isLive
              ? "bg-emerald-500/20 hover:bg-emerald-500/30 border-emerald-500/50"
              : "bg-amber-500/20 hover:bg-amber-500/30 border-amber-500/50"
          } border rounded-xl ${isLive ? "text-emerald-100" : "text-amber-100"} font-medium text-sm transition-all hover:scale-[1.02]`}
        >
          <Github className="w-4 h-4" />
          {isLive ? "View Source" : "Clone & Run Locally"}
          <ArrowRight className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}
