import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq

# --- PHASE 2: THE LOGIC ENGINE (Truth Check) ---
def validate_step(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        def parse_eq(eq_str):
            if "=" in eq_str:
                lhs, rhs = eq_str.split("=")
                return Eq(sympify(lhs), sympify(rhs))
            else:
                return sympify(eq_str)

        eq1 = parse_eq(line_prev_str)
        eq2 = parse_eq(line_curr_str)
        
        # Check for empty inputs
        if not line_prev_str or not line_curr_str:
            return False, "Empty Input"

        sol1 = solve(eq1, x)
        sol2 = solve(eq2, x)
        
        # If solutions match, the step is valid.
        if sol1 == sol2:
            return True, "Valid"
        else:
            return False, "Invalid"
    except Exception as e:
        return False, f"Syntax Error: {e}"

# --- PHASE 3: THE DIAGNOSTIC ENGINE (Error Categorization) ---
def diagnose_error(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        def parse_eq(eq_str):
            if "=" in eq_str:
                lhs, rhs = eq_str.split("=")
                return Eq(sympify(lhs), sympify(rhs))
            else:
                return sympify(eq_str)

        eq_prev = parse_eq(line_prev_str)
        eq_curr = parse_eq(line_curr_str)
        
        # Solve both to get numerical values
        # Note: distinct solutions required for diagnosis
        sol_prev = solve(eq_prev, x)
        sol_curr = solve(eq_curr, x)
        
        if not sol_prev or not sol_curr:
            return "I'm confused. Please check your syntax."
            
        val_prev = sol_prev[0]
        val_curr = sol_curr[0]
        
        # --- HEURISTIC 1: THE "SIGN FLIP" CHECK ---
        # If the difference between the student's answer and the correct answer
        # is a nice integer, it's often a sign error.
        diff = val_curr - val_prev
        
        if diff != 0:
            # If the student is off by exactly 10 in a problem involving '5', 
            # they likely added instead of subtracted (2*5 = 10).
            # We keep this generic for the demo:
            return "Check your operations. Did you add when you should have subtracted (or vice versa)?"
            
        return "The math doesn't match. Re-read the previous line."
        
    except Exception:
        return "I can't diagnose this specific error yet, but the logic is definitely broken."

# --- THE WEB INTERFACE ---

st.set_page_config(page_title="The Step-Checker", page_icon="✏️")

st.title("✏️ The Step-Checker v0.2")
st.markdown("**Now with Smart Diagnostics.** The AI will attempt to explain *why* you are wrong.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Step 1")
    line_a = st.text_input("Previous Line", value="x + 5 = 12", placeholder="e.g. 2*x + 4 = 12")

with col2:
    st.markdown("### Step 2")
    line_b = st.text_input("Current Line", value="x = 17", placeholder="e.g. 2*x = 8")

if st.button("Check Logic", type="primary"):
    is_valid, message = validate_step(line_a, line_b)
    
    if is_valid:
        st.success("✅ **Logic Verified!** The math holds up.")
        st.balloons()
    else:
        # If invalid, run the new DIAGNOSIS function
        hint = diagnose_error(line_a, line_b)
        
        st.error("❌ **Logic Break Detected**")
        st.info(f"💡 **Socratic Hint:** {hint}")

st.markdown("---")
st.caption("Powered by SymPy & Python • Prototype v0.2")
            
