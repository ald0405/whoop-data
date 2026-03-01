# Protein Recommendation Tool Integration

## Overview
The protein recommendation tool has been integrated into the agent system to provide personalized protein intake recommendations based on the user's current weight (from Withings) and activity level.

## Implementation

### Tool Definition
**Location:** `whoopdata/agent/tools.py`

**Function:** `get_protein_recommendation_tool(activity_level: str)`

**Features:**
- Automatically fetches latest weight data from Withings
- Calculates protein range based on activity level
- Returns personalized recommendation with context

### Protein Multipliers
Based on evidence-based guidelines (g/kg bodyweight):

| Activity Level | Protein Range (g/kg) |
|----------------|---------------------|
| Normal | 1.2 - 1.4 |
| Endurance Training | 1.2 - 1.4 |
| Resistance/Strength Training | 1.6 - 2.2 |

### Activity Levels
The tool accepts three activity level options:
1. `"normal"` - Sedentary/light activity
2. `"endurance training"` - Running, cycling, swimming
3. `"resistance/strength training"` - Weightlifting, strength work

## Agent Integration

### 1. Health Data Agent
The tool is available to the `health_data` specialist agent for general health data queries.

**Registry Entry:** `AGENT_REGISTRY["health_data"]`

**Tools Available:**
- `get_protein_recommendation`
- `get_weight_data`
- Other health metrics...

### 2. Nutrition Specialist Agent (NEW)
A new dedicated nutrition specialist agent has been created.

**Registry Entry:** `AGENT_REGISTRY["nutrition"]`

**Description:** Handles nutrition guidance and protein intake recommendations.

**System Prompt:** Provides evidence-based nutrition recommendations with focus on protein intake calculations.

**Tools Available:**
- `get_protein_recommendation` - Main recommendation tool
- `get_weight_data` - Access to weight history
- `get_workout_data` - Workout context for activity level

## Usage

### Direct Tool Usage
```python
from whoopdata.agent.tools import get_protein_recommendation_tool

# Get recommendation for endurance athlete
result = await get_protein_recommendation_tool(
    activity_level="endurance training"
)
# Returns: "Based on your current weight of 70.0kg and 'endurance training' 
#           activity level, aim for 84g - 98g protein per day"
```

### Through the Agent System
Users can ask questions like:
- "How much protein should I eat?"
- "What's my protein target for strength training?"
- "Give me a protein recommendation"

The supervisor will route to the appropriate specialist (health_data or nutrition).

## Error Handling

The tool handles various error scenarios:

1. **No weight data available:**
   - Returns: "Need more info: No weight data available. Please log your weight first."

2. **Invalid activity level:**
   - Returns: "Need more info: Invalid activity level. Please choose from: 'normal', 'endurance training', 'resistance/strength training'"

3. **API errors:**
   - Propagates weight data errors
   - Returns descriptive error messages

## Testing

A test script is available at `test_protein_tool.py`:

```bash
python test_protein_tool.py
```

Tests include:
1. Weight data retrieval
2. Normal activity recommendation
3. Endurance training recommendation
4. Resistance training recommendation
5. Invalid activity level handling

## Integration Flow

```
User Query: "How much protein should I eat for strength training?"
    ↓
Supervisor Agent
    ↓
Routes to: Nutrition Specialist
    ↓
Asks user for activity level (if not provided)
    ↓
Calls: get_protein_recommendation_tool(activity_level="resistance/strength training")
    ↓
Tool internally calls: get_weight_data_tool(latest=True)
    ↓
Fetches weight from: /withings/weight API endpoint
    ↓
Calculates: weight_kg * (1.6 to 2.2)
    ↓
Returns: "Based on your current weight of 70.0kg and 'resistance/strength training' 
          activity level, aim for 112g - 154g protein per day"
    ↓
Nutrition Agent adds context about distribution/timing
    ↓
Response to User
```

## Future Enhancements

Potential improvements:
1. Add meal planning suggestions
2. Integrate with workout type to auto-suggest activity level
3. Track protein intake over time
4. Add macronutrient balance recommendations (carbs/fats)
5. Create protein timing recommendations around workouts
6. Add vegetarian/vegan protein source suggestions

## Dependencies

- `get_weight_data_tool` - Depends on Withings API being functional
- Weight data must be available in the system
- User must have logged at least one weight measurement

## API Requirements

Ensure the following endpoint is available:
- `GET /withings/weight?latest=true` - Returns latest weight measurement
