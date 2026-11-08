from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Tiger Data (TimescaleDB) connection string
    timescale_service_url: str

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_ms: int = 25_000
    # Total time we give Gemini for one document before the local parser takes over
    extraction_budget_s: int = 45
    # Tried in order when the primary model is out of quota (429) or overloaded (503). Quotas are per model.
    gemini_fallback_models: str = "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-2.5-flash"
    # Cache of extraction results keyed by file hash: repeat uploads are instant and need no API call
    extraction_cache_dir: str = "extraction_cache"

    # Auth0 (optional until wired; when unset, a demo applicant is used)
    auth0_domain: str = ""
    auth0_audience: str = ""

    # App
    app_base_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"

    # Rough FX to USD for the landlord view (per 1 USD). Update in .env if needed.
    fx_to_usd: str = "RWF=1400,KES=129,NGN=1550,GHS=15.5,UGX=3700,TZS=2600,XOF=600,XAF=600,EUR=0.92,GBP=0.79,USD=1,HTG=131,BRL=5.6,DOP=60,COP=4200,MXN=18.5"

    @property
    def fx_table(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for pair in self.fx_to_usd.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                try:
                    out[k.strip().upper()] = float(v)
                except ValueError:
                    pass
        return out


settings = Settings()  # type: ignore[call-arg]
