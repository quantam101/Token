import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "@/lib/api";

export default function UsedByStrip() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    client
      .get("/showcase/savings?limit=10")
      .then(({ data }) => setRows(data.customers || []))
      .catch(() => {});
  }, []);

  if (!rows.length) return null;

  // Duplicate the rows so the marquee loops seamlessly
  const loop = [...rows, ...rows];

  return (
    <section data-testid="used-by-strip" className="relative border-t border-[rgb(var(--tf-border))]">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="font-mono text-xs uppercase tracking-widest text-[rgb(var(--tf-text-muted))] text-center mb-6">
          USED BY · LIVE SAVINGS FROM REAL CUSTOMERS
        </div>
        <div className="relative overflow-hidden" style={{ maskImage: "linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)", WebkitMaskImage: "linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent)" }}>
          <div className="tf-marquee flex gap-3 whitespace-nowrap w-max">
            {loop.map((r, i) => (
              <Link
                key={`${r.slug}-${i}`}
                to={`/share/${r.slug}`}
                data-testid={`usedby-pill-${r.slug}`}
                className="inline-flex items-center gap-3 border border-[rgb(var(--tf-border))] bg-[rgb(var(--tf-bg-2))] hover:border-[rgb(var(--tf-success))] hover:text-white px-4 py-2 rounded-full transition-colors group"
              >
                <span className="w-2 h-2 rounded-full bg-[rgb(var(--tf-success))] animate-pulse" />
                <span className="text-sm text-white font-medium">{r.display_name}</span>
                <span className="text-xs font-mono text-[rgb(var(--tf-text-muted))] group-hover:text-[rgb(var(--tf-success))]">
                  saved {r.tokens_saved.toLocaleString()} tk
                </span>
                <span className="text-xs font-mono text-[rgb(var(--tf-brand))]">
                  ${r.cost_saved_usd.toFixed(2)}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
