use crate::domain::inference::command::LlmInferenceCommand;

pub fn parse_inference_requested(payload: &str) -> Result<LlmInferenceCommand, String> {
    // Adapter boundary: raw Kafka payload -> domain command used by inference slice.
    // Граница адаптера: сырой payload из Kafka -> доменная команда для inference slice.
    serde_json::from_str::<LlmInferenceCommand>(payload).map_err(|e| e.to_string())
}
