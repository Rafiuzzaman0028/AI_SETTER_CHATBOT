

# API Documentation

## Overview
This service operates a dual-system AI architecture for social media lead generation:
1. **Comment Bot (The Doorbell):** A stateless, high-speed, logic-based system that reads public comments and redirects users to the DMs.
2. **AI Setter (The Closer):** A stateful, LLM-powered chatbot with conversational memory that qualifies leads via DMs and routes them to high-ticket coaching or low-ticket courses.

**Base URL:** `http://<YOUR_VPS_IP>:8000` *(Update with actual domain when deployed)*  
**Data Format:** `application/json`

---

## 1. AI Setter API (DM Chatbot)

### `POST /process-message`
Processes a direct message from a user, updates their qualification attributes, calculates the next conversation state, and generates a human-like reply. 

*Note: Conversational memory (chat history) is handled internally via Redis using the `user_id`.*

#### **Request Body**
```json
{
  "user_id": "string",
  "message": "string",
  "current_state": "string",
  "user_attributes": "object" 
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | `string` | Yes | Unique identifier for the user (e.g., IG Handle or DB ID). Used to fetch chat history from Redis. |
| `message` | `string` | Yes | The actual text message sent by the user. |
| `current_state` | `string` | Yes | The state returned from the *previous* AI response. **Must be exactly `ENTRY` for a brand new conversation.** |
| `user_attributes` | `object` | Optional | A JSON object containing extracted user data. You must pass back the `extracted_attributes` object you received from the previous response. |

#### **Example Request**
```json
{
    "user_id": "ig_user_8892",
    "message": "Dating is just really frustrating right now.",
    "current_state": "STAGE_1_PATTERN",
    "user_attributes": {
        "current_state_turn_count": 0
    }
}
```

#### **Response Body**
```json
{
  "reply": "string",
  "next_state": "string",
  "extracted_attributes": "object",
  "progress_score": "integer"
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `reply` | `string` | The exact text the bot should send back to the user. |
| `next_state` | `string` | The new state of the conversation. **The backend must save this and send it in the next request.** |
| `extracted_attributes` | `object` | JSON object containing data the AI has learned (e.g., `age`, `financial_bucket`, `location_region`). **The backend must save this and pass it back in the next request.** |
| `progress_score` | `integer` | A value from `0` to `100` representing how far the user has progressed through the sales funnel. Useful for UI progress bars or lead scoring. |

#### **Example Response**
```json
{
    "reply": "it seems like this is a pattern. how long has this been going on for you... months, years?",
    "next_state": "STAGE_2_TIME_COST",
    "extracted_attributes": {
        "current_state_turn_count": 0,
        "primary_problem": "CONFIDENCE"
    },
    "progress_score": 25
}
```

---

## 2. Memory Management API

### `DELETE /clear-history/{user_id}`
Wipes the conversational memory (Redis cache) for a specific user. 

**When to use this:**
*   When a user completes the funnel and you want to reset them for the future.
*   During QA/Testing to start a fresh conversation with the same test ID.

#### **Request Parameters**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | `string` | Yes | Passed in the URL path. |

#### **Example Response**
```json
{
    "status": "cleared"
}
```

---

## 3. Comment Bot API (Public Comments)

### `POST /process-comment`
A fast, stateless endpoint to handle public comments on Instagram, Facebook, or YouTube. It detects the user's intent (Price, Eligibility, Interest) and returns a locked template response directing them to send a DM.

#### **Request Body**
```json
{
  "platform": "string",
  "user_id": "string",
  "comment_text": "string",
  "post_id": "string"
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `platform` | `string` | Optional | E.g., `"INSTAGRAM"`, `"YOUTUBE"`, `"FACEBOOK"`. Influences wording (e.g., YT requires "@yourpage" tag). |
| `user_id` | `string` | Yes | The ID of the commenter. |
| `comment_text` | `string` | Yes | The raw comment text. |
| `post_id` | `string` | Optional | ID of the post (useful for your own backend logging). |

#### **Example Request**
```json
{
    "platform": "INSTAGRAM",
    "user_id": "ig_user_123",
    "comment_text": "How much does the coaching cost?"
}
```

#### **Response Body**
```json
{
    "reply_text": "I’ll explain the pricing properly 👍\nDM us on Instagram",
    "intent_detected": "PRICE",
    "action": "POST_REPLY"
}
```

---

## 🚦 System State Reference (For Backend Devs)

The AI Setter moves through a strict linear funnel. Here are the valid states for reference:

| Phase | State Name | Progress Score | Description |
| :--- | :--- | :--- | :--- |
| **Warm-up** | `ENTRY` <br> `ENTRY_SOCIAL` | 0 <br> 10 | Greetings and social pivot. |
| **Sales Funnel** | `STAGE_1_PATTERN` <br> `STAGE_2_TIME_COST` <br> `STAGE_3_ADDITIONAL` <br> `STAGE_4_FAILED_SOLUTIONS` <br> `STAGE_5_GOAL` <br> `STAGE_6_GAP` <br> `STAGE_7_REFRAME` <br> `STAGE_8_INTRO_COACHING` <br> `STAGE_9_PROGRAM_FRAMING` | 15 <br> 25 <br> 35 <br> 45 <br> 55 <br> 65 <br> 70 <br> 75 <br> 80 | The psychological sequence identifying pain points and introducing the solution. |
| **Qualification** | `STAGE_10_QUAL_LOCATION` <br> `STAGE_10_QUAL_AGE` <br> `STAGE_10_QUAL_RELATIONSHIP` <br> `STAGE_10_QUAL_FITNESS` <br> `STAGE_10_QUAL_FINANCE` | 85 <br> 88 <br> 90 <br> 92 <br> 95 | Hard filter questions to determine the routing outcome. |
| **Routing & Close** | `POST_LINK_FLOW` <br> `END` | 100 <br> 100 | The user has received their link. The bot acts as a "Relationship Manager" for post-sale questions, tech issues, etc. |

---

## 🛑 Error Handling

The API will return standard HTTP status codes:

*   **`200 OK`**: Request processed successfully.
*   **`400 Bad Request`**: Invalid input data (e.g., passing an unrecognized `current_state` string).
*   **`422 Unprocessable Entity`**: Missing required fields based on the JSON schema.
*   **`500 Internal Server Error`**: An unexpected failure (e.g., Redis connection failed, OpenAI API timeout). If this occurs, the backend should prompt the user with a graceful fallback message (e.g., *"Just glitched for a second, what was that?"*).
