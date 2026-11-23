# SmartLogix — Sprint 5: Administration, Analytics & Release

**Sprint goal:** Give admins oversight (overview, team management, analytics) and finish the release.

This archive is the **cumulative, runnable state of the project at the end of Sprint 5**.
(Suggested sprint length: 2 weeks — adjust to your team's calendar.)

## Roadmap
| Sprint | Theme | |
| Sprint 1 | Foundation & Authentication |
| Sprint 2 | Product Catalogue & Inventory |
| Sprint 3 | Cart, Checkout & Order Placement |
| Sprint 4 | Order Fulfilment & Delivery Tracking |
| Sprint 5 | Administration, Analytics & Release | 

## Sprint backlog (user stories)
| ID | User story | Acceptance criteria |
|---|---|---|
| US-17 | As admin, I see an overview of orders, customers, products and delayed orders. | Stat cards, recent orders and low-stock list are shown. |
| US-18 | As admin, I can change user roles. | Role changes take effect at the user's next login. |
| US-19 | As admin, I can view analytics. | Orders-by-status and 7-day revenue charts render. |
| US-20 | As the team, we have a tested, documented release. | All 17 tests pass; README and setup steps verified. |

## Tasks completed
- [x] Admin dashboard queries
- [x] Team & roles page
- [x] Analytics page (Chart.js)
- [x] Admin permission tests
- [x] Final regression test and documentation

## Increment delivered
- Everything from Sprint 4
- Admin dashboard: totals, potential-delay count, recent orders, low-stock attention list
- Team & roles page to promote users to warehouse / delivery / admin
- Analytics: orders-by-status chart and 7-day revenue trend
- Full test suite (17 tests) and final documentation = release candidate

## Sprint review / demo script
1. Log in as admin and review the overview
2. Change a user to Warehouse in Team & roles
3. Open Analytics
4. Run `pytest -q` (17 passing)

## Definition of Done
- [x] Code runs locally (`python app.py`) against MySQL using `database/schema.sql`
- [x] Unit tests for the sprint's features pass (`pytest -q`)
- [x] Role permissions checked for every new route
- [x] Documentation (README + this file) updated

## Next sprint
Backlog ideas: payments, email/SMS notifications, live map tracking, demand forecasting.

## Retrospective (fill in with your team)
- What went well:
- What to improve:
- Actions for next sprint:
