use async_trait::async_trait;
use tokio::sync::mpsc;

use crate::application::inference_slice::ports::LlmEnginePort;

pub struct OllamaClient;

#[async_trait]
impl LlmEnginePort for OllamaClient {
    async fn generate_stream(
        &self,
        _model: &str,
        prompt: &str,
    ) -> Result<mpsc::Receiver<String>, String> {
        let (tx, rx) = mpsc::channel(16);
        let base = format!("Mocked Ollama answer for: {prompt}");
        tokio::spawn(async move {
            for token in base.split_whitespace() {
                let _ = tx.send(format!("{token} ")).await;
            }
        });
        Ok(rx)
    }
}
