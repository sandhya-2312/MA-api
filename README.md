# MA FastAPI Backend

## Deployment workflow (Render + Vercel)

1. Connect the Render web service to the Render PostgreSQL database so `DATABASE_URL` is injected automatically.
2. Set the frontend URL in `FRONTEND_ORIGINS` and deploy the Vercel app with `VITE_API_URL` pointing at the Render API.
3. Redeploy the backend so build migrations and startup bootstrap run against the production database.
4. If production should reuse existing local users, projects, assignments, and project data, copy application data before the first login test:
   - `SOURCE_DATABASE_URL=postgresql://...local...`
   - `TARGET_DATABASE_URL=postgresql://...render...`
   - `python -m scripts.copy_application_data`
5. Configure deployment login accounts on Render when a role account is missing:
   - `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD`
   - `INITIAL_USER_USERNAME` / `INITIAL_USER_PASSWORD`
   - `INITIAL_VIEWER_USERNAME` / `INITIAL_VIEWER_PASSWORD`
6. Keep `INITIAL_*_FIRST_LOGIN=false` for existing accounts that should open their dashboard immediately after login.
7. Sign in at the Vercel `/login` page with the matching role credentials:
   - Admin opens the admin dashboard.
   - User opens assigned project workflows.
   - Viewer opens read-only assigned project views.
8. Check `GET /health` for database connectivity and table counts after deploy.

## Setup

1. Create and activate virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure environment variables in `.env`.
4. Apply migrations: `python -m alembic upgrade head`
5. **First admin (empty database):**
   - `python -m backend.create_initial_admin <username> <password>`
   - Password must be at least 8 characters. Sign in via the app and complete First Login Setup if prompted.
6. Run API:
   - `uvicorn backend.main:app --reload`
   - Or: `python dev_start.py` (reload; does **not** seed users)

## Cleaning demo / sample data

Legacy demo accounts from older seeds (`operator`, `viewer`) and optional project wipe:

```bash
# Remove operator & viewer only
python -m backend.cleanup_demo_data

# Also delete the old seeded admin username "admin" if you still have it
python -m backend.cleanup_demo_data --remove-legacy-admin

# Remove all projects (and related entries) — use when you want an empty project list
python -m backend.cleanup_demo_data --wipe-all-projects

# Full local reset of demo users + all projects
python -m backend.cleanup_demo_data --remove-legacy-admin --wipe-all-projects
```

Optional: `python -m backend.seed_dev_users` is a no-op unless you add entries to `DEV_USERS` in `backend/seed_dev_users.py`.

## Migrations (Alembic)

- Create migration history table and mark current DB at latest revision:
  - `alembic stamp head`
- Apply migrations:
  - `alembic upgrade head`
- Create a new migration after model changes:
  - `alembic revision --autogenerate -m "describe change"`

## Implemented APIs

- `POST /login`
- `POST /change-password`
- `POST /users`
- `GET /users`
- `DELETE /users/{id}`
- `PUT /users/{id}`
- `GET /profile`
- `PUT /profile`
- `POST /projects`
- `GET /projects`
- `PUT /projects/{project_id}`
- `DELETE /projects/{project_id}`
- `POST /assign-user`
- `POST /data`
- `PUT /data/{data_id}`
- `DELETE /data/{data_id}`
- `GET /dashboard-data?project_id=1`
- `GET /dashboard-data/bulk?project_ids=1,2,3&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`
- `GET /reports/project/{project_id}/summary`

### Endpoint notes

- `DELETE /data/{data_id}`
  - Deletes one data entry (Admin or assigned User).
- `GET /dashboard-data/bulk`
  - Fetches points for multiple projects in one call.
  - Optional filters:
    - `project_ids` (comma-separated ids)
    - `from_date` and `to_date` in `YYYY-MM-DD`
- `GET /reports/project/{project_id}/summary`
  - Exports a CSV report for a project summary.
  - Requires project access (Admin or assigned User/Viewer).

## Roles and Permissions

- `Admin`: Full CRUD for users and projects, all data access.
- `User`: Access assigned projects, add project data, view assigned dashboard data.
- `Viewer`: Read-only access to assigned dashboard data.
