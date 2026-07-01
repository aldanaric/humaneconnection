Grace - Oriana Andre Growth plan parts
1. Purpose & Approach  
2. Development Priorities  
3. 30-Day Implementation Timeline  
4. Supervisory Environment for Growth  
5. Success Indicators  
6. Sustaining High Performance  
7. How Performance Thrives Through Humane Connection  
8. Why Behavior-Change Science Amplifies These Effects

Dynamic Sections (Specific to Employee)
Purpose and approach
Executive summary of the plan
Establishes the “why” and names the frameworks being used
System Role: system will need to synthesize raw manager feedback and the employee's role/personality to generate a 1-2 sentence core objective.

Development Priorities
Behavioral engine: takes abstract goals and breaks them down into actions
Tells the employee what to do and the manager how to support them
System Role: The AI needs to take a weakness (e.g., "doesn't ask questions"), define a Behavioral Goal, link it to the framework (Humane Connection), and generate a realistic habit loop based on their daily workflow.

30-Day Implementation Timeline
Chronological matrix mapping the priorities from Section 2 into a week-by-week schedule.
Prevents overwhelm so the employee doesn't try to do everything at once while also establishing accountability for both employee and supervisor
System Role: The AI prompt here acts as a scheduler, extracting the actions from Section 2 and distributing them logically across four weeks, generating concrete indicators of progress for each.

Success Indicators
What is the definition of done → short list of observable changes
Provides objective criteria for 30 day review
System Role: Your system will need to summarize the "Rewards" and "Behavioral Goals" from Section 2 into definitive, measurable statements.

Environment and Sustaining Factors
Supervisory Environment for growth
Guide for managers on how to adapt their leadership style for this employee’s plan
This section holds the supervisor accountable for modeling the right behaviors and creating psychological safety.
System Role: The AI will need to map the employee's development priorities to corresponding management techniques (e.g., if the employee is working on "Analytical Scaffolding," the manager is prompted to "Conduct joint logic reviews").

Sustaining High Performance
Long term maintenance strategy
Bridges the gap between 30 day plan and permanent change
System Role: The system generates identity anchors and team rituals based on the personality type (e.g., an INTJ might need a structured "30-Day Checkpoint," whereas an ENFP might need more frequent, informal team shoutouts).

Static Methodology (Same for every employee)
How Performance Thrives Through Humane Connection
Why Behavior-Change Science Amplifies These Effects

The Diagnostic Engine Prompt
Copy and paste this into the system prompt, placed right after you define the AI's role and before the document generation instructions:
### STEP 1: THE DIAGNOSTIC ENGINE (Internal Reasoning)  
Before generating any part of the 30-Day Growth Plan, you MUST conduct a diagnostic analysis of the employee. You will not output this analysis in the final document; it is your internal reasoning to determine the strategic posture of the plan.
Analyze the provided inputs (Role, Personality Type, Core Functions, Manager Feedback) using the following four steps:
1.  **Role Demands:** What is the fundamental requirement of this job? (e.g., An Analyst must synthesize ambiguity into truth; an Admin must manage chaos into order).  
2.  **Personality Friction:** Based on the Personality Type provided, what is this person's natural default behavior? Where does this natural default conflict with the Role Demands?  
*   *Example:* An INTJ (Architect) wants certainty and perfection before speaking, but an Analyst role requires navigating high ambiguity and iteration.  
3.  **Identify the Core Vulnerability:** Synthesize the friction into a single, defining behavioral trap. Use one of these archetypes if applicable, or define a new one:  
*   *Analysis Paralysis* (Fear of being wrong leading to silence/delay)  
*   *Boundary Collapse* (People-pleasing leading to burnout/overextension)  
*   *Execution Isolation* (Doing the work alone to avoid collaborative friction)  
*   *Reactivity Loop* (Constantly putting out fires instead of building systems)  
4.  **Define the Strategic Posture:** Based on the Core Vulnerability, determine the fundamental purpose of this plan. Choose the primary intervention:  
*   *Accelerate:* Force them to act sooner, share messy drafts, and ask questions.  
*   *Protect:* Force them to slow down, build boundaries, and say "not yet."  
*   *Connect:* Force them to integrate with the team and communicate process, not just outcomes.
**OUTPUT DIRECTIVE:**  
Generate your Diagnostic Engine output in a JSON block at the very beginning of your response. Use this exact structure:
{  
"diagnostic_engine": {  
"role_demands": "...",  
"personality_friction": "...",  
"core_vulnerability": "...",  
"strategic_posture": "..."  
}  
}
Only after completing this JSON block may you begin generating the actual text for the 30-Day Growth Plan. All methods, habits, and supervisory advice generated in the plan MUST directly solve the "core_vulnerability" and align with the "strategic_posture."