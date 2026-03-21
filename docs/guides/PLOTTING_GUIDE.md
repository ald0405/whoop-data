# Plotting Guide for Health Data Agent

## Overview
The health data agent can now create and display visualizations directly in chat! Plots are automatically captured and embedded as images in your conversation.

## How It Works

### User Experience
1. Ask the agent to create a plot
2. Agent writes Python code to analyze data and create visualization
3. Code is executed and plot is saved
4. **Image automatically appears in chat** (like ChatGPT!)
5. Agent provides analysis based on the visualization

### Example Queries

**Simple Plot:**
```
Plot my recovery scores for the last 30 days
```

**Multiple Metrics:**
```
Show me 3 charts: recovery trend, HRV over time, and sleep efficiency
```

**Custom Analysis:**
```
Create a scatter plot of my HRV vs recovery score to see the correlation
```

**Comparative Analysis:**
```
Plot my tennis workout strain compared to running workouts over the last 3 months
```

## Technical Details

### For Developers

The plotting capability is implemented through:

1. **PythonREPLWithImages tool** (`whoopdata/agent/tools.py`):
   - Wraps standard PythonREPLTool
   - Detects new .png/.jpg/.jpeg files after code execution
   - Base64-encodes images
   - Returns JSON with `{"output": "...", "images": [...]}`

2. **Enhanced System Prompt** (`whoopdata/agent/nodes.py`):
   - Tells agent about visualization capabilities
   - Provides examples of when to plot

3. **Gradio Image Embedding** (`chat_app.py`):
   - Parses tool results for image data
   - Embeds base64 images as HTML: `<img src="data:image/png;base64,{data}"/>`
   - Images display inline in chat messages

### Code Execution Environment

The Python REPL has these libraries available:
- **Data**: pandas, numpy, json
- **Plotting**: matplotlib, seaborn
- **Stats**: scipy, scikit-learn

Matplotlib is pre-configured for headless operation (no display window needed).

### Best Practices for Plotting

When the agent creates plots, it should:
1. Use unique filenames (e.g., `recovery_plot_001.png`)
2. Set appropriate figure size: `plt.figure(figsize=(10, 6))`
3. Add clear titles and labels
4. Use high DPI for crisp images: `plt.savefig('plot.png', dpi=150, bbox_inches='tight')`
5. Close figures after saving: `plt.close()`

### File Management

- Images are detected in the current working directory
- Files are automatically cleaned up after encoding
- Each session can generate multiple plots
- No manual file management needed

## Troubleshooting

### Images Not Displaying
1. Check that matplotlib is using 'Agg' backend
2. Verify plt.savefig() is called with .png extension
3. Check Gradio console for JSON parsing errors

### Code Execution Errors
- Agent has full Python environment
- Can install packages if needed with pip
- Check error messages in tool output

### Performance
- First plot generation may be slower (matplotlib initialization)
- Base64 encoding adds minimal overhead
- Large/complex plots may increase response time

## Examples

### Agent Workflow Example

**User:** "Plot my recovery trend"

**Agent Process:**
1. Calls `get_recovery_data_tool(latest=False, limit=30)`
2. Writes Python code to parse JSON and create plot
3. Executes code with `python_interpreter` tool
4. Tool detects generated `recovery_plot.png`
5. Image is base64-encoded and returned
6. Gradio embeds image in chat
7. Agent provides analysis: "Your recovery shows..."

**User Sees:**
```
[Agent text explaining what it's doing]

[Python code block showing matplotlib code]

[Image of recovery trend graph]

[Analysis text about the trend]
```

## LangSmith Compatibility

When using LangSmith Studio for debugging:
- Tool executions show in trace
- Base64 image data visible in tool output
- LangSmith automatically renders images in trace view
- No special handling needed

## Future Enhancements

Potential improvements:
- Interactive plots with Plotly
- Multiple plots side-by-side
- Plot download buttons
- Chart type preferences
- Custom styling/themes
