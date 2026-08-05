from unittest.mock import MagicMock, patch
from app.llm_client import GroqLLMClient

@patch("app.llm_client.Groq")
def test_complete_sends_system_and_user_messages(mock_groq_cls):
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="hello"))]
    mock_client.chat.completions.create.return_value = mock_response

    llm = GroqLLMClient(api_key="fake-key")
    result = llm.complete(system="sys", user="usr")

    assert result == "hello"
    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][1] == {"role": "user", "content": "usr"}
