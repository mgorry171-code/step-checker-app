import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex

# --- SETUP SESSION STATE (The Memory) ---
# We need to initialize memory slots for the inputs so buttons can modify them.
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x + 5 = 12"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""

# --- HELPER FUNCTIONS ---
def add_to_curr(text_to_add):
    """Adds text to the 'Current Line' input"""
    st.session_state.line_curr += text_to_add

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
        
        sol_prev = solve(eq_prev, x)
        sol_curr = solve(eq_curr, x)
        
        if not sol_prev or not sol_curr:
            return "Syntax error."
            
        val_prev = sol_prev[0]
        val_curr = sol_curr[0]
        
        diff = val_curr - val_prev
        if diff != 0:
            return "Check your operations. Did you add when you should have subtracted?"
            
        return "The math doesn't match."
        
    except Exception:
        return "Logic broken (Complex error)."

# --- THE WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v0.3", page_icon="🧮")

st.title("🧮 Step-Checker v0.3")
st.caption("Now with Math Keys & Live Preview")

# --- INPUT SECTION ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Previous Line")
    # We bind this input to session_state.line_prev
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    
    # LIVE PREVIEW (Render the LaTeX)
    if st.session_state.line_prev:
        try:
            # Convert text to fancy math
            st.latex(st.session_state.line_prev.replace("*", "")) 
        except:
            st.caption("...")

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    
    # LIVE PREVIEW
    if st.session_state.line_curr:
        try:
             st.latex(st.session_state.line_curr.replace("*", ""))
        except:
             st.caption("...")

# --- THE MATH KEYBOARD ---
st.markdown("##### ⌨️ Quick Keys (Adds to Current Line)")
k1, k2, k3, k4, k5 = st.columns(5)

# Each button calls 'add_to_curr' with specific text
k1.button("x²", on_click=add_to_curr, args=("**2",), help="Add squared exponent")
k2.button("√x", on_click=add_to_curr, args=("sqrt(",), help="Add Square Root")
k3.button("÷", on_click=add_to_curr, args=("/",), help="Add Division")
k4.button("(", on_click=add_to_curr, args=("(",))
k5.button(")", on_click=add_to_curr, args=(")",))

st.markdown("---")

# --- ACTION BUTTON ---
if st.button("Check Logic", type="primary"):
    # Grab values from state
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, message = validate_step(line_a, line_b)
    
    if is_valid:
        st.success("✅ **Logic Verified!**")
        st.balloons()
    else:
        hint = diagnose_error(line_a, line_b)
        st.error("❌ **Logic Break**")
        st.info(f"💡 {hint}")
