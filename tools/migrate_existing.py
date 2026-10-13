"""Import the existing project's model settings without copying its .env."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.models import ModelSettings, read_env

root = Path(__file__).resolve().parents[1]
source = root.parent / 'ai-interview-agent' / '.env'
settings = ModelSettings(root)
if settings.public()['has_key']:
    print('Existing encrypted model configuration preserved.')
else:
    values = read_env(source)
    if values.get('LLM_API_KEY'):
        settings.update({'mode':'online', 'api_key':values['LLM_API_KEY'],
                         'base_url': values.get('LLM_BASE_URL') or 'https://api.deepseek.com/v1',
                         'model': values.get('LLM_MODEL') or 'deepseek-chat', 'redact_contacts': True})
        print('Original model configuration imported; API Key encrypted for this Windows account.')
    else:
        print('No original API Key found; offline mode is ready.')
