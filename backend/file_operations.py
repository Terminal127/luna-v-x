from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from pathlib import Path

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3000"] for specific frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

ENV_PATH = Path(".env")

class ConfigUpdate(BaseModel):
    provider: str
    model: str
    api_key: str

def update_env_variable(key: str, value: str) -> None:
    if not ENV_PATH.exists():
        ENV_PATH.write_text("")

    lines = ENV_PATH.read_text().splitlines()
    updated = False

    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f'{key}="{value}"'
            updated = True
            break

    if not updated:
        lines.append(f'{key}="{value}"')

    ENV_PATH.write_text("\n".join(lines))

@app.post("/update-config")
def update_config(config: ConfigUpdate) -> Dict[str, str]:
    update_env_variable("MODEL_PROVIDER", config.provider)
    update_env_variable("MODEL_NAME", config.model)
    update_env_variable("MODEL_API_KEY", config.api_key)
    return {"status": "success", "message": "Configuration updated in .env"}

@app.get("/current-config")
def current_config() -> Dict[str, str | None]:
    config_data: Dict[str, str | None] = {
        "provider": None,
        "model": None,
        "api_key": None
    }
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("MODEL_PROVIDER="):
                config_data["provider"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("MODEL_NAME="):
                config_data["model"] = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("MODEL_API_KEY="):
                config_data["api_key"] = line.split("=", 1)[1].strip().strip('"')
    return config_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
