import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # JWT authentication settings
    SECRET_KEY: str = Field("defaultsecretkeypleasechange", alias="SECRET_KEY")
    ALGORITHM: str = Field("HS256", alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # MySQL Settings
    MYSQL_HOST: str = Field("mysql-db", alias="MYSQL_HOST")
    MYSQL_PORT: int = Field(3306, alias="MYSQL_PORT")
    MYSQL_USER: str = Field("land_app", alias="MYSQL_USER")
    MYSQL_PASSWORD: str = Field("AppPassword123!", alias="MYSQL_PASSWORD")
    MYSQL_DB: str = Field("devdb", alias="MYSQL_DB")
    MYSQL_ADMIN_USER: str = Field("admin", alias="MYSQL_ADMIN_USER")
    MYSQL_ADMIN_PASSWORD: str = Field("Admin1234!", alias="MYSQL_ADMIN_PASSWORD")

    # PostgreSQL Settings
    POSTGRES_HOST: str = Field("postgres-db", alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, alias="POSTGRES_PORT")
    POSTGRES_USER: str = Field("land_app", alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("AppPassword123!", alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("devdb", alias="POSTGRES_DB")
    POSTGRES_ADMIN_USER: str = Field("admin", alias="POSTGRES_ADMIN_USER")
    POSTGRES_ADMIN_PASSWORD: str = Field("Admin1234!", alias="POSTGRES_ADMIN_PASSWORD")

    # Oracle Settings
    ORACLE_HOST: str = Field("oracle-db", alias="ORACLE_HOST")
    ORACLE_PORT: int = Field(1521, alias="ORACLE_PORT")
    ORACLE_USER: str = Field("land_app", alias="ORACLE_USER")
    ORACLE_PASSWORD: str = Field("AppPassword123!", alias="ORACLE_PASSWORD")
    ORACLE_SERVICE: str = Field("XE", alias="ORACLE_SERVICE")
    ORACLE_ADMIN_USER: str = Field("admin", alias="ORACLE_ADMIN_USER")
    ORACLE_ADMIN_PASSWORD: str = Field("Admin1234!", alias="ORACLE_ADMIN_PASSWORD")

    # MS SQL Server Settings
    MSSQL_HOST: str = Field("mssql-db", alias="MSSQL_HOST")
    MSSQL_PORT: int = Field(1433, alias="MSSQL_PORT")
    MSSQL_USER: str = Field("land_app", alias="MSSQL_USER")
    MSSQL_PASSWORD: str = Field("AppPassword123!", alias="MSSQL_PASSWORD")
    MSSQL_DB: str = Field("devdb", alias="MSSQL_DB")
    MSSQL_ADMIN_USER: str = Field("sa", alias="MSSQL_ADMIN_USER")
    MSSQL_ADMIN_PASSWORD: str = Field("Admin1234!", alias="MSSQL_ADMIN_PASSWORD")

    # MongoDB Settings
    MONGO_HOST: str = Field("mongodb", alias="MONGO_HOST")
    MONGO_PORT: int = Field(27017, alias="MONGO_PORT")
    MONGO_USER: str = Field("land_app", alias="MONGO_USER")
    MONGO_PASSWORD: str = Field("AppPassword123!", alias="MONGO_PASSWORD")
    MONGO_DB: str = Field("devdb", alias="MONGO_DB")
    MONGO_AUTH_DB: str = Field("admin", alias="MONGO_AUTH_DB")
    MONGO_ADMIN_USER: str = Field("admin", alias="MONGO_ADMIN_USER")
    MONGO_ADMIN_PASSWORD: str = Field("Admin1234!", alias="MONGO_ADMIN_PASSWORD")

    # Connection pooling configurations
    POOL_SIZE: int = 15
    MAX_OVERFLOW: int = 25

    # Config source
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
