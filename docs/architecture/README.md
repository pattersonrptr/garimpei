# Garimpei architecture

C4 model diagrams for Garimpei. They are written in Mermaid, so GitHub renders them
directly and every change shows up as a normal text diff.

PNG versions (for places that don't render Mermaid) are in [`images/`](images/).
To regenerate them after editing this file, run from the repository root:

```bash
npx -y @mermaid-js/mermaid-cli -i docs/architecture/README.md -o docs/architecture/images/c4.png -s 3 -b white
```

## Level 1: System context

Who uses Garimpei and which external systems it depends on.

```mermaid
flowchart TB
    user["<b>User</b><br/>[Person]<br/>Creates price alerts and<br/>follows opportunities"]
    admin["<b>Administrator</b><br/>[Person]<br/>Manages users, searches<br/>and source websites"]
    system["<b>Garimpei</b><br/>[Software system]<br/>Tracks marketplace prices, keeps their history<br/>and alerts users about opportunities"]
    markets["<b>Marketplaces</b><br/>[External system]<br/>OLX, Mercado Livre,<br/>Enjoei, Estante Virtual"]
    sendgrid["<b>Email provider</b><br/>[External system]<br/>SendGrid, or any SMTP server"]
    proxy["<b>Proxy providers</b><br/>[External system, optional]<br/>Fallback for blocked IPs"]

    user -->|"Manages alerts and views<br/>prices, using HTTPS"| system
    admin -->|"Administers the platform,<br/>using HTTPS"| system
    system -->|"Scrapes public listings,<br/>using a headless browser"| markets
    system -->|"Sends alert emails,<br/>SendGrid API or SMTP"| sendgrid
    system -.->|"Routes scraper traffic"| proxy
    sendgrid -.->|"Delivers alert email"| user

    classDef person fill:#0B3D73,stroke:#082C54,color:#fff
    classDef main fill:#1F6FBF,stroke:#17578F,color:#fff
    classDef external fill:#6B7280,stroke:#4B5563,color:#fff
    class user,admin person
    class system main
    class markets,sendgrid,proxy external
```

## Level 2: Containers

The separately running parts of the system. Scrapers have no database access: everything
they read or store goes through the API.

```mermaid
flowchart TB
    user["<b>User or administrator</b><br/>[Person]"]

    subgraph garimpei["Garimpei"]
        flower["<b>Flower</b><br/>[Container: Flower]<br/>Monitors Celery tasks"]
        frontend["<b>Frontend</b><br/>[Container: React 19, Vite, MUI, nginx]<br/>Web interface"]
        beat["<b>Scheduler</b><br/>[Container: Celery Beat]<br/>Builds the schedule from active alerts"]
        api["<b>Backend API</b><br/>[Container: FastAPI, SQLAlchemy]<br/>Owns the data and business rules:<br/>auth, alerts, plans, notifications"]
        redis[("<b>Redis</b><br/>[Container: Redis]<br/>Task broker, task results<br/>and search locks")]
        db[("<b>Database</b><br/>[Container: PostgreSQL 13]<br/>Users, alerts, products,<br/>price history, logs")]
        worker["<b>Scraper workers</b><br/>[Container: Celery, Playwright]<br/>Search marketplaces and<br/>collect product data"]
    end

    sendgrid["<b>Email provider</b><br/>[External system]<br/>SendGrid or SMTP"]
    markets["<b>Marketplaces</b><br/>[External system]"]

    user -.->|"Monitors tasks, HTTP"| flower
    user -->|"Uses, HTTP"| frontend
    flower -->|"Reads task events"| redis
    frontend -->|"Calls, JSON:API over HTTP"| api
    beat -->|"Reads active alerts, HTTP"| api
    beat -->|"Queues scheduled runs"| redis
    api -->|"Queues manual runs"| redis
    api -->|"Reads and writes, SQL"| db
    api -->|"Sends email"| sendgrid
    redis -->|"Delivers tasks"| worker
    worker -->|"Reads configs and saves<br/>products, HTTP"| api
    worker -->|"Scrapes, Playwright"| markets

    classDef person fill:#0B3D73,stroke:#082C54,color:#fff
    classDef container fill:#1F6FBF,stroke:#17578F,color:#fff
    classDef store fill:#17578F,stroke:#0B3D73,color:#fff
    classDef external fill:#6B7280,stroke:#4B5563,color:#fff
    class user person
    class frontend,api,beat,worker,flower container
    class db,redis store
    class markets,sendgrid external
    style garimpei fill:#F3F7FB,stroke:#1F6FBF,stroke-dasharray:6 4,color:#0B3D73
```

## Level 3: Backend API components

Clean Architecture layers inside the API. Dependencies point inward: the web layer
and the infrastructure depend on use cases and domain, never the other way around.
Persistence and email sit behind interfaces, so adding the SMTP backend next to
SendGrid did not touch any use case.

```mermaid
flowchart TB
    client["<b>Frontend or scraper workers</b><br/>[Client]"]

    subgraph api["Backend API"]
        controllers["<b>Web layer</b><br/>[FastAPI, Pydantic, JWT]<br/>Controllers, schemas, JSON:API<br/>presenters, auth, plan-limit checks"]
        usecases["<b>Use cases</b><br/>[Application layer]<br/>Alerts, products, notifications"]
        limits["<b>Plan rules</b><br/>[Domain layer: plain Python]<br/>Limits and violations per plan,<br/>no framework imports"]
        ports["<b>Interfaces</b><br/>[Python ABC]<br/>Repositories and email service"]
        entities["<b>Entities and validators</b><br/>[Domain layer: Pydantic]<br/>Alert, Product, Plan, User"]
        repositories["<b>Repositories and models</b><br/>[Infrastructure: SQLAlchemy]<br/>Implement persistence"]
        email["<b>Email services</b><br/>[Infrastructure: SendGrid SDK, smtplib]<br/>One implementation per provider"]
        celeryclient["<b>Celery client</b><br/>[Infrastructure: Celery]<br/>Queues manual runs"]
    end

    subgraph outside[" "]
        direction LR
        db[("<b>PostgreSQL</b>")]
        mail["<b>Email provider</b><br/>[External system]<br/>SendGrid or SMTP"]
        redis[("<b>Redis</b>")]
    end

    client -->|"HTTP"| controllers
    controllers --> usecases
    controllers --> limits
    controllers --> celeryclient
    usecases --> ports
    usecases --> entities
    limits --> entities
    ports -.->|"Implemented by"| repositories
    ports -.->|"Implemented by"| email
    entities ~~~ celeryclient
    repositories --> db
    email --> mail
    celeryclient --> redis

    classDef component fill:#1F6FBF,stroke:#17578F,color:#fff
    classDef infra fill:#3E8E7E,stroke:#2F6F62,color:#fff
    classDef store fill:#17578F,stroke:#0B3D73,color:#fff
    classDef external fill:#6B7280,stroke:#4B5563,color:#fff
    class controllers,usecases,ports,entities,limits component
    class repositories,email,celeryclient infra
    class db,redis store
    class client,mail external
    style api fill:#F3F7FB,stroke:#1F6FBF,color:#0B3D73
    style outside fill:none,stroke:none
```

## Level 3: Scraper components

How the Celery workers turn one search into saved products.

```mermaid
flowchart LR
    beat["<b>Celery Beat</b><br/>[Scheduler]"]
    api["<b>Backend API</b><br/>[FastAPI]"]
    redis[("<b>Redis</b><br/>Task queue<br/>and search lock")]

    subgraph workers["Scraper workers"]
        direction TB
        runsearch["<b>run_scraper_search</b><br/>[Celery task]<br/>Takes the lock, starts<br/>one search per site"]
        search["<b>run_search</b><br/>[Celery task]<br/>Collects product URLs"]
        process["<b>process_urls_list</b><br/>[Celery task]<br/>Splits URLs into batches of 20"]
        batch["<b>scrape_batch</b><br/>[Celery task]<br/>Scrapes a batch with one browser"]
        save["<b>save_products</b><br/>[Celery task]<br/>Saves data, triggers alert evaluation"]
        runsearch --> search --> process --> batch --> save
    end

    subgraph engine["Scraping engine and API access"]
        direction TB
        manager["<b>ScraperManager and ScraperFactory</b><br/>[Python]<br/>Create and run the right scraper"]
        scrapers["<b>Site scrapers</b><br/>[Playwright]<br/>OLX, Mercado Livre,<br/>Enjoei, Estante Virtual"]
        proxy["<b>Proxy rotators</b><br/>[Python, optional]<br/>Paid or free proxies"]
        client["<b>ApiClient</b><br/>[requests]<br/>Authenticated API calls"]
        manager --> scrapers
        scrapers -.-> proxy
    end

    markets["<b>Marketplaces</b><br/>[External system]"]
    apiOut["<b>Backend API</b><br/>[FastAPI]"]

    beat -->|"Queues search"| redis
    api -->|"Queues manual search"| redis
    redis -->|"Delivers task"| runsearch
    batch -->|"run_search and scrape_batch<br/>use the scrapers"| manager
    save -->|"run_scraper_search and<br/>save_products call the API"| client
    scrapers -->|"Site scrapers open a<br/>headless browser"| markets
    client -->|"ApiClient sends<br/>JSON:API over HTTP"| apiOut

    classDef component fill:#1F6FBF,stroke:#17578F,color:#fff
    classDef store fill:#17578F,stroke:#0B3D73,color:#fff
    classDef external fill:#6B7280,stroke:#4B5563,color:#fff
    class runsearch,search,process,batch,save,manager,scrapers,proxy,client component
    class redis store
    class beat,api,apiOut,markets external
    style workers fill:#F3F7FB,stroke:#1F6FBF,color:#0B3D73
    style engine fill:#F3F7FB,stroke:#1F6FBF,color:#0B3D73
```
