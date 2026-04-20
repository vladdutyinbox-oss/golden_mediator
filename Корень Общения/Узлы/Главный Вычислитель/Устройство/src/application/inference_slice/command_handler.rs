use crate::application::inference_slice::service::InferenceService;
use crate::domain::inference::command::LlmInferenceCommand;
use crate::domain::inference::event::InferenceEvent;

pub async fn handle_llm_inference_requested(
    service: &InferenceService,
    command: LlmInferenceCommand,
) -> Result<Vec<InferenceEvent>, String> {
    service.handle_command(command).await
}
