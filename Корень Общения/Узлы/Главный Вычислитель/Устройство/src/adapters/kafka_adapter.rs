use crate::domain::inference::command::LlmInferenceCommand;

pub fn parse_inference_requested(payload: &str) -> Result<LlmInferenceCommand, String> {
    serde_json::from_str::<LlmInferenceCommand>(payload).map_err(|e| e.to_string())
}
