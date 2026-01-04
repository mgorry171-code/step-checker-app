import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq

# --- THE LOGIC ENGINE (Copy-Pasted from your previous success) ---

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
        
        if sol1 == sol2:
            return True, "Valid"
        else:
            return False, "Invalid"
    except Exception as e:
        return False, f"Syntax Error: {e}"

def get_hint(prev_line, curr_line):
    # A simple version of Phase 3 (Diagnostics) for the Demo
    # In a full app, this would check specific error types.
    return "Check your math. Did you perform the same operation on both sides?"

# --- THE WEB INTERFACE ---

st.set_page_config(page_title="The Step-Checker", page_icon="✏️")

st.title("✏️ The Step-Checker Prototype")
st.write("Enter two lines of algebra below. The AI will check if your logic holds up.")

# Create two columns for a nice layout
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Step 1")
    line_a = st.text_input("Previous Line", value="2*x + 4 = 12", placeholder="e.g. 2*x + 4 = 12")

with col2:
    st.markdown("### Step 2")
    line_b = st.text_input("Current Line", value="2*x = 8", placeholder="e.g. 2*x = 8")

# The "Check" Button
if st.button("Check Logic", type="primary"):
    is_valid, message = validate_step(line_a, line_b)
    
    if is_valid:
        st.success("✅ **Logic Verified!** The math holds up.")
        st.balloons() # Fun animation
    else:
        st.error("❌ **Logic Break Detected**")
        
        # Simulated Socratic Hint
        hint = get_hint(line_a, line_b)
        st.info(f"💡 **Socratic Hint:** {hint}")
        
        # specific check for the "Sign Error" demo
        if "17" in line_b and "12" in line_a:
             st.warning("It looks like you added 5 instead of subtracting it!")

st.markdown("---")
st.caption("Powered by SymPy & Python • Prototype v0.1")