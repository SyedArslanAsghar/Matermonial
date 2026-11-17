# Matermonial — AWS Deployment and CI/CD Strategy

**Version:** 1.0  
**Date:** 11 November 2026

## 1. Deployment objectives

Deploy the Matermonial application to AWS EC2 using Docker and Docker Compose.

The deployment must support:

- Secure production configuration.
- HTTPS.
- PostgreSQL persistence.
- Django API workers.
- Celery workers.
- Redis.
- Private media storage.
- Background scheduling.
- Monitoring and logging.
- Automated CI/CD.
- Database backups.
- Rollback and recovery.

## 2. Deployment architecture

Recommended initial production topology:

```text
                 Internet
                    |
                    v
              DNS / Domain
                    |
                    v
               HTTPS / TLS
                    |
                    v
             Nginx Reverse Proxy
                    |
             +------+------+
             |             |
             v             v
         React Web     Django API
          Frontend       Workers
                            |
                  +---------+---------+
                  |         |         |
                  v         v         v
              PostgreSQL  Redis    Private S3
                  |         |
                  |         v
                  |       Celery
                  |       Workers
                  |       Beat/Scheduler
                  |
                  v
              Backups
```

This is a recommended initial topology. Database and Redis hosting may be moved to managed AWS services when budget, reliability, and operational requirements justify it.

## 3. AWS services

Recommended services:

- EC2: application deployment host.
- EBS: persistent storage where required.
- S3: private media and export storage.
- IAM: least-privilege permissions.
- CloudWatch: logs, metrics, and alarms.
- Route 53: DNS if selected.
- AWS Certificate Manager or another suitable certificate process depending on the chosen ingress architecture.
- AWS Backup or a documented PostgreSQL backup process.

RDS PostgreSQL and managed Redis are future operational options, not mandatory assumptions for the first EC2 deployment.

## 4. Docker strategy

Docker is required for production deployment, not mandatory for local development.

Recommended production services:

- `nginx`
- `backend`
- `celery_worker`
- `celery_beat`
- `redis`
- `frontend` or a static frontend deployment service
- `postgres` only if the selected initial deployment topology intentionally hosts PostgreSQL on EC2

For production, evaluate whether PostgreSQL should run on EC2 or a managed database service. Do not put a production database in an ephemeral container without persistent storage and a tested backup/recovery plan.

## 5. Container requirements

- Use production Dockerfiles.
- Use non-root users where practical.
- Pin base images.
- Avoid embedding secrets in images.
- Use `.dockerignore`.
- Keep images reasonably small.
- Use health checks.
- Use persistent volumes only where required.
- Do not expose internal service ports publicly.
- Use explicit container restart policies.
- Keep application and database lifecycles separate.

## 6. Environment configuration

Maintain separate configurations for:

- Local.
- Test.
- Staging.
- Production.

Production environment variables include:

- Django secret key.
- Debug disabled.
- Allowed hosts.
- Database connection.
- Redis connection.
- Celery configuration.
- Email credentials.
- SMS credentials.
- JazzCash credentials.
- Object-storage settings.
- Domain and trusted origins.
- Logging configuration.

Inject secrets through a secure deployment mechanism. Do not commit production environment files.

## 7. Network security

- Expose only required public ports.
- Restrict SSH access.
- Prefer restricted administrative access or a secure management channel.
- Do not expose PostgreSQL publicly.
- Do not expose Redis publicly.
- Use security groups with least privilege.
- Enforce HTTPS.
- Configure appropriate firewall rules.
- Keep OS packages and container images updated.

## 8. Nginx responsibilities

Nginx should:

- Terminate or route HTTPS according to the selected TLS design.
- Route API traffic to Django.
- Serve or route frontend assets.
- Apply upload-size limits.
- Forward appropriate headers.
- Configure request timeouts.
- Avoid exposing private media directories.
- Support health checks.
- Use secure headers where appropriate.

## 9. Database operations

- Use PostgreSQL.
- Persist database data.
- Back up regularly.
- Encrypt backups at rest.
- Restrict backup access.
- Monitor disk usage.
- Test restore procedures.
- Apply migrations as a controlled deployment step.
- Avoid running multiple competing migration processes.

## 10. Media storage

Production should use private object storage.

Separate storage prefixes or buckets for:

- Profile photos.
- Identity verification documents.
- Message attachments.
- Shared documents.
- Moderation evidence.
- Data exports.

Apply least-privilege IAM policies and retention rules.

## 11. Celery deployment

Run separate processes for:

- General asynchronous tasks.
- Scheduled tasks through Celery Beat.
- Specialized queues where task volume or priority requires them.

Requirements:

- Worker health monitoring.
- Retry policy.
- Task time limits.
- Idempotency.
- Dead-letter or failed-task visibility.
- Safe shutdown.
- No duplicate scheduler instances unless the scheduler architecture explicitly supports them.

## 12. CI/CD workflow

Recommended GitHub Actions pipeline:

```text
Developer Push / Pull Request
             |
             v
        Install Dependencies
             |
             v
       Lint and Static Checks
             |
             v
          Run Tests
             |
             v
      Build Frontend/Backend
             |
             v
       Validate Migrations
             |
             v
        Build Images
             |
             v
       Publish Images
             |
             v
       Deploy to Staging
             |
             v
       Smoke Tests
             |
             v
      Production Approval
             |
             v
      Deploy to Production
             |
             v
       Health Verification
```

## 13. CI requirements

Pull request checks should include:

- Ruff.
- Backend tests.
- Frontend lint.
- Frontend tests.
- TypeScript checks.
- Build checks.
- Migration checks.
- OpenAPI schema validation.
- Dependency/security checks where configured.

## 14. Deployment requirements

The deployment process should:

1. Verify the target branch and release.
2. Build immutable images.
3. Publish versioned images.
4. Back up the database where appropriate.
5. Pull the approved image version.
6. Apply reviewed migrations.
7. Restart application services.
8. Restart or update Celery workers.
9. Verify health endpoints.
10. Run smoke tests.
11. Report deployment status.
12. Retain the previous known-good image for rollback.

Avoid uncontrolled destructive database migrations.

## 15. Rollback strategy

Application rollback should use a previous immutable image.

Database rollback is not always safely reversible. Prefer backward-compatible migrations:

1. Add new schema.
2. Deploy code that supports old and new fields.
3. Migrate data.
4. Switch application usage.
5. Remove obsolete schema in a later release.

Do not automatically reverse a destructive migration during emergency rollback.

## 16. Monitoring

Monitor:

- API availability.
- HTTP error rates.
- Response times.
- CPU and memory.
- Disk usage.
- Database connections.
- Redis availability.
- Celery queue length.
- Task failures.
- Payment callback failures.
- Notification delivery failures.
- Export/deletion task failures.
- Backup success/failure.

Set alerts for critical operational failures.

## 17. Backup and disaster recovery

Define:

- Backup frequency.
- Retention duration.
- Encryption.
- Backup location.
- Access permissions.
- Recovery Point Objective (RPO).
- Recovery Time Objective (RTO).
- Restore test schedule.

RPO/RTO values must be confirmed according to the business's actual availability and budget requirements. Do not invent guarantees.

Test restoring both database and required media references.

## 18. Production launch checklist

- Domain and DNS configured.
- HTTPS working.
- Debug disabled.
- Allowed hosts configured.
- Secrets securely injected.
- Database protected.
- Redis protected.
- Private storage verified.
- Admin MFA enabled.
- Payment callbacks verified.
- Celery worker and scheduler healthy.
- Monitoring active.
- Backups enabled.
- Restore test completed.
- CI/CD production approval enabled.
- Rollback procedure documented.
- Security and privacy checks passed.
- Smoke tests passed.