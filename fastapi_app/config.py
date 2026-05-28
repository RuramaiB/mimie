import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # JWT authentication settings
    SECRET_KEY: str = Field("defaultsecretkeypleasechange", alias="SECRET_KEY")
    ALGORITHM: str = Field("HS256", alias="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # MySQL Settings
    MYSQL_HOST: str = Field("mysql-c", alias="MYSQL_HOST")
    MYSQL_PORT: int = Field(3306, alias="MYSQL_PORT")
    MYSQL_USER: str = Field("melissa", alias="MYSQL_USER")
    MYSQL_PASSWORD: str = Field("admin@melissa", alias="MYSQL_PASSWORD")
    MYSQL_DB: str = Field("melissa-db", alias="MYSQL_DB")
    MYSQL_ADMIN_USER: str = Field("melissa", alias="MYSQL_ADMIN_USER")
    MYSQL_ADMIN_PASSWORD: str = Field("admin@melissa", alias="MYSQL_ADMIN_PASSWORD")

    # PostgreSQL Settings
    POSTGRES_HOST: str = Field("postgres-c", alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, alias="POSTGRES_PORT")
    POSTGRES_USER: str = Field("melissa", alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("admin@melissa", alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("melissa-db", alias="POSTGRES_DB")
    POSTGRES_ADMIN_USER: str = Field("melissa", alias="POSTGRES_ADMIN_USER")
    POSTGRES_ADMIN_PASSWORD: str = Field("admin@melissa", alias="POSTGRES_ADMIN_PASSWORD")

    # Oracle Settings
    ORACLE_HOST: str = Field("oracle-c", alias="ORACLE_HOST")
    ORACLE_PORT: int = Field(1521, alias="ORACLE_PORT")
    ORACLE_USER: str = Field("melissa", alias="ORACLE_USER")
    ORACLE_PASSWORD: str = Field("admin@melissa", alias="ORACLE_PASSWORD")
    ORACLE_SERVICE: str = Field("melissadb", alias="ORACLE_SERVICE")
    ORACLE_ADMIN_USER: str = Field("melissa", alias="ORACLE_ADMIN_USER")
    ORACLE_ADMIN_PASSWORD: str = Field("admin@melissa", alias="ORACLE_ADMIN_PASSWORD")

    # MS SQL Server Settings
    MSSQL_HOST: str = Field("mssql-c", alias="MSSQL_HOST")
    MSSQL_PORT: int = Field(1433, alias="MSSQL_PORT")
    MSSQL_USER: str = Field("melissa", alias="MSSQL_USER")
    MSSQL_PASSWORD: str = Field("admin@melissa", alias="MSSQL_PASSWORD")
    MSSQL_DB: str = Field("melissa-db", alias="MSSQL_DB")
    MSSQL_ADMIN_USER: str = Field("sa", alias="MSSQL_ADMIN_USER")
    MSSQL_ADMIN_PASSWORD: str = Field("admin@melissa", alias="MSSQL_ADMIN_PASSWORD")

    # MongoDB Settings
    MONGO_HOST: str = Field("mongodb-c", alias="MONGO_HOST")
    MONGO_PORT: int = Field(27017, alias="MONGO_PORT")
    MONGO_USER: str = Field("melissa", alias="MONGO_USER")
    MONGO_PASSWORD: str = Field("admin@melissa", alias="MONGO_PASSWORD")
    MONGO_DB: str = Field("melissa-db", alias="MONGO_DB")
    MONGO_AUTH_DB: str = Field("admin", alias="MONGO_AUTH_DB")
    MONGO_ADMIN_USER: str = Field("melissa", alias="MONGO_ADMIN_USER")
    MONGO_ADMIN_PASSWORD: str = Field("admin@melissa", alias="MONGO_ADMIN_PASSWORD")

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
