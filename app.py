import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x**2 = 16"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""

# --- HELPER FUNCTIONS ---
def add_to_curr(text_to_add):
    st.session_state.line_curr += text_to_add

def pretty_print(math_str):
    try:
        # Handle +/- manually for display if user tries to type it
        clean_str = math_str.replace("+/-", "±")
        if "=" in clean_str:
            lhs, rhs = clean_str.split("=")
            lat_lhs = latex(sympify(lhs))
            lat_rhs = latex(sympify(rhs))
            return f"{lat_lhs} = {lat_rhs}"
        else:
            return latex(sympify(clean_str))
    except:
        return None

def validate_step(line_prev_str, line_curr_str):
    x = symbols('x')
    try:
        def parse_eq(eq_str):
            # Pre-clean known human syntax issues
            eq_str = eq_str.replace("^", "**") # Allow using ^ for exponents
            
            if "=" in eq_str:
                lhs, rhs = eq_str.split("=")
                return Eq(sympify(lhs), sympify(rhs))
            else:
                return sympify(eq_str)

        eq1 = parse_eq(line_prev_str)
        eq2 = parse_eq(line_curr_str)
        
        if not line_prev_str or not line_curr_str:
            return False, "Empty Input"

        sol1 = solve(eq1, x)
        sol2 = solve(eq2, x)
        
        # --- THE NEW LOGIC ---
        
        # 1. Perfect Match
        if sol1 == sol2:
            return True, "Valid"
        
        # 2. Subset Match (The "Partial Credit" Logic)
        # If the student's answer (e.g., 4) is IN the previous solution set (-4, 4)
        set1 = set(sol1)
        set2 = set(sol2)
        
        if set2.issubset(set1) and len(set2) > 0:
            return True, "Partial" # We return True so it passes, but we can flag it
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

def diagnose_error(line_prev_str, line_curr_str):
    # (Same diagnostic code as before, simplified for space)
    return "Check your math logic."

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v0.5", page_icon="🧮")
st.title("🧮 Step-Checker v0.5")
st.caption("Now with 'Partial Credit' Logic & ^ Support")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Previous Line")
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    if st.session_state.line_prev:
        st.latex(pretty_print(st.session_state.line_prev))

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    if st.session_state.line_curr:
        st.latex(pretty_print(st.session_state.line_curr))

st.markdown("##### ⌨️ Quick Keys")
k1, k2, k3, k4, k5 = st.columns(5)
k1.button("x²", on_click=add_to_curr, args=("**2",))
k2.button("√x", on_click=add_to_curr, args=("sqrt(",))
k3.button("÷", on_click=add_to_curr, args=("/",))
k4.button("(", on_click=add_to_curr, args=("(",))
k5.button(")", on_click=add_to_curr, args=(")",))

st.markdown("---")

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, status = validate_step(line_a, line_b)
    
    if is_valid and status == "Valid":
        st.success("✅ **Perfect Logic!**")
        st.balloons()
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
        st.write("You found one valid solution ($x=4$), but did you miss another one? Remember: $x^2 = 16$ has two roots!")
    else:
        st.error("❌ **Logic Break**")
