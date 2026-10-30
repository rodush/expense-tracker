# Architecture

It is a monolith multi-tier application: frontend, backend, database storage.

Frontend application is served from the same server which powers API and business logic.

It uses relational database (SQLite on local, PostgreSQL in Production) to store processed data persistently.
ORM is used to abstract database access.

For the sake of speeding this up, it uses in-memory, read-through, caching for repeated reads.
