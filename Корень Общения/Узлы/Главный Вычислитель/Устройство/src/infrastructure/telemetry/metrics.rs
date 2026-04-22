use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

#[derive(Default)]
pub struct MetricsRegistry {
    inference_latency_ms: AtomicU64,
    tokens_per_second_x100: AtomicU64,
    vram_usage_gb_x100: AtomicU64,
    throughput_rps_x100: AtomicU64,
    chunks_published: AtomicU64,
}

impl MetricsRegistry {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn record_inference_elapsed(&self, elapsed: Duration, tokens: u64, vram_gb: f64) {
        let ms = elapsed.as_millis() as u64;
        self.inference_latency_ms.store(ms, Ordering::Relaxed);

        let sec = elapsed.as_secs_f64();
        let tps = if sec > 0.0 { tokens as f64 / sec } else { 0.0 };
        self.tokens_per_second_x100
            .store((tps * 100.0) as u64, Ordering::Relaxed);
        self.vram_usage_gb_x100
            .store((vram_gb * 100.0) as u64, Ordering::Relaxed);

        let rps = if sec > 0.0 { 1.0 / sec } else { 0.0 };
        self.throughput_rps_x100
            .store((rps * 100.0) as u64, Ordering::Relaxed);
    }

    pub fn inference_latency_ms(&self) -> u64 {
        self.inference_latency_ms.load(Ordering::Relaxed)
    }

    pub fn tokens_per_second(&self) -> f64 {
        self.tokens_per_second_x100.load(Ordering::Relaxed) as f64 / 100.0
    }

    pub fn vram_usage_gb(&self) -> f64 {
        self.vram_usage_gb_x100.load(Ordering::Relaxed) as f64 / 100.0
    }

    pub fn throughput_rps(&self) -> f64 {
        self.throughput_rps_x100.load(Ordering::Relaxed) as f64 / 100.0
    }

    pub fn inc_chunks_published(&self) {
        self.chunks_published.fetch_add(1, Ordering::Relaxed);
    }

    pub fn chunks_published(&self) -> u64 {
        self.chunks_published.load(Ordering::Relaxed)
    }
}
