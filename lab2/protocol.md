# Lab 2: Coffee Shop TCP Wire Protocol Specification

Transport: Raw TCP socket
Framing: Newline-delimited text (`\n` or `\r\n`). Every request and response MUST end with `\n`.
Encoding: UTF-8

---

## 1. Handshake / Identification

Immediately upon TCP connection establishment:

- **Client**:
  - Send: `ROLE client\n`
  - Server response: `OK role_accepted\n`
- **Provider**:
  - Send: `ROLE provider\n`
  - Server response: `OK role_accepted\n`

If an invalid role is provided:
- Server response: `ERROR invalid_role\n` and socket is closed.

---

## 2. Client Commands

### 2.1 Get Menu & Stock
- **Request**: `GET_MENU\n`
- **Response**: `MENU coffee=<int> tea=<int> croissant=<int>\n`
- **Example**: `MENU coffee=15 tea=22 croissant=8\n`

### 2.2 Place Order
- **Request**: `ORDER <item>=<qty> [<item>=<qty> ...]\n`
  - Valid items: `coffee` (4s), `tea` (3s), `croissant` (2s)
  - Quantities must be positive integers.
- **Immediate Response (Success)**:
  - `ORDER_ACCEPTED id=<int> wait_time=<seconds>\n`
- **Immediate Response (Failure - Out of Stock)**:
  - `ORDER_REFUSED reason=insufficient_stock coffee_left=<int> tea_left=<int> croissant_left=<int>\n`
- **Immediate Response (Failure - Invalid Input)**:
  - `ERROR invalid_order: <details>\n`
- **Asynchronous Notification (When order is completed by worker)**:
  - `ORDER_READY id=<int>\n`

---

## 3. Provider Commands & Alerts

### 3.1 Deliver Stock
- **Request**: `DELIVER <item>=<qty> [<item>=<qty> ...]\n`
  - Quantities must be positive integers.
- **Response (Success)**:
  - `DELIVERY_OK coffee=<int> tea=<int> croissant=<int>\n`
- **Response (Unauthorized Client Attempt)**:
  - `ERROR unauthorized_role\n`

### 3.2 Low Stock Alert (Server Push)
- Triggered automatically whenever any product's stock drops below 5.
- If provider is connected: server pushes immediately:
  - `ALERT_LOW_STOCK product=<name> count=<int>\n`
- If provider is not connected: server queues the alert and sends it immediately after provider completes handshake (`ROLE provider`).

---

## 4. Error Responses
Any unparseable command or invalid action receives:
`ERROR <error_message>\n`

---

## 5. Disconnect & Failure Protocol (Task 4)
- When client disconnects unexpectedly (TCP FIN / RST):
  - Server cancels all orders belonging to that client in the FIFO waiting queue.
  - Server signals the active worker (if an order is currently being prepared) to abort.
  - All reserved items are returned to stock immediately.
  - Whatever preparation time elapsed is discarded.
- When server disconnects:
  - Client / Provider terminates cleanly with a notification message.
