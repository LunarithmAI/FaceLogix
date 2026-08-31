# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Operations leaders responsible for attendance, workforce administration, and facility workflows. Technical evaluators are a secondary audience when reviewing deployment and security.

## Product Purpose

FaceLogix records employee check-in and check-out through face recognition with liveness and image-quality checks. It gives organization operators one place to manage people, devices, attendance records, reports, and bulk enrollment.

## Positioning

FaceLogix combines self-hosted attendance operations with an internal ONNX inference service. Enrollment images are converted into embeddings and are not retained, while liveness checks and revocable device credentials protect the attendance workflow.

## Operating Context

Organizations enroll people individually or through atomic ZIP and CSV imports, provision attendance devices, record check-ins and check-outs, review attendance, and export reports as CSV. The application is responsive and installable on desktop, tablet, and mobile.

## Capabilities and Constraints

- Organization-scoped users, roles, devices, attendance, and reports
- Face enrollment and attendance with liveness and image-quality checks
- Atomic bulk import for up to 100 people with explicit conflict resolution
- Revocable device credentials and refresh-token sessions
- PostgreSQL 16 with pgvector as the only stateful infrastructure dependency
- Single-host Docker Compose production deployment behind Nginx and TLS
- GitHub Pages hosts only the separate static marketing page, not the authenticated product

## Brand Commitments

The product name is FaceLogix. Public copy should be direct, operational, and technically credible. The primary landing-page action is to view the open-source repository on GitHub.

## Evidence on Hand

- Product capabilities and deployment details in `README.md`
- Existing React application in `frontend/`
- Existing FaceLogix favicon and application icons in `frontend/public/`
- No customer logos, testimonials, usage benchmarks, pricing, or hosted product demo are available and none should be fabricated

## Product Principles

- Make attendance fast without weakening identity checks.
- Keep biometric processing under the operator's control.
- Make operational failures visible and recoverable.
- Prefer verifiable system behavior over marketing claims.
- Keep deployment and data ownership understandable.

## Accessibility & Inclusion

The landing page must support keyboard navigation, visible focus states, reduced motion, readable contrast, and responsive layouts across desktop and mobile web.
