import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import select, func
from app.models.candidate import Application, Job, Candidate

async def check():
    async with AsyncSessionLocal() as db:
        # Count applications
        result = await db.execute(select(func.count(Application.id)))
        app_count = result.scalar()
        
        # Count jobs
        result = await db.execute(select(func.count(Job.id)))
        job_count = result.scalar()
        
        # Count candidates
        result = await db.execute(select(func.count(Candidate.id)))
        cand_count = result.scalar()
        
        print(f'Applications: {app_count}')
        print(f'Jobs: {job_count}')
        print(f'Candidates: {cand_count}')
        
        # Show applications per job
        result = await db.execute(
            select(Job.id, Job.title, func.count(Application.id))
            .outerjoin(Application, Job.id == Application.job_id)
            .group_by(Job.id, Job.title)
        )
        for job_id, title, count in result.all():
            print(f'Job "{title}": {count} applications')

if __name__ == "__main__":
    asyncio.run(check())