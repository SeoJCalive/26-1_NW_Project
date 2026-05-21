# Web UI Feedback Revision Deduplication Matrix

| Fact | Authoritative Location | Allowed Secondary Location | Remove From |
|---|---|---|---|
| Node identity | `NodeCard` title and `DetailPanel` header | none | traffic rows and activity logs when repeated verbatim |
| Node role | `NodeCard` short code plus `DetailPanel` runtime id | peer cards only when describing the opposite endpoint | global summaries |
| Liveness | `NodeCard` badge | `DetailPanel` basic information row | activity logs |
| Processing state | fixed dashboard slot `dashboard-slot-processing-state` | selected node header status chip | raw `state` text rows |
| Queue depth | fixed dashboard slot `dashboard-slot-queue-depth` | none | raw card text and common summary strings |
| Pending ACK | fixed dashboard slot `dashboard-slot-pending-ack` | traffic response text when explaining a waiting hop | repeated pending summaries |
| Retry | fixed dashboard slot `dashboard-slot-retry-policy` | R2 traffic/Monitor board when explaining timeout behavior | generic retry/duplicate combined rows |
| Duplicate handling | fixed dashboard slot `dashboard-slot-duplicate-handling` | Monitor board when explaining final sink health | activity log metric restatement |
| Previous hop | `TrafficBoard` previous peer card | hop summary compact row | node card |
| Next hop | `TrafficBoard` next peer card | hop summary compact row | node card |
| Event lineage | `TrafficBoard` recent flow | timeline overview | common node summary |
| Recent activity | `ActivityLogSection` | none | node card, common fields, monitor health slots |
| Control/status affordance | page chrome and command palette | none | graph canvas, node cards, hub-like visual objects |
| Data path | diagram graph and `mainLinks` | page caption | page chrome and controller-like report links |

Result: the graph owns topology, cards own compact node state, detail owns expanded node facts, traffic/monitor boards own flow interpretation, logs own recent activity, and page chrome owns browser-level control affordances.
