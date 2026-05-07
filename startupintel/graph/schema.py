CONSTRAINTS = [
    "CREATE CONSTRAINT startup_id IF NOT EXISTS FOR (s:Startup) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT investor_id IF NOT EXISTS FOR (i:Investor) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT founder_id IF NOT EXISTS FOR (f:Founder) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT accelerator_id IF NOT EXISTS FOR (a:Accelerator) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT acquirer_id IF NOT EXISTS FOR (q:Acquirer) REQUIRE q.id IS UNIQUE",
]


async def apply_schema(driver) -> None:
    async with driver.session() as session:
        for statement in CONSTRAINTS:
            await session.run(statement)

