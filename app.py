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
        clean_str = math_str.replace("+/-", "±")
        if "=" in clean_str:
            lhs, rhs = clean_str.split("=")
            # If there's a comma in the answer (4, -4), we just latex the string directly
            # to avoid SymPy getting confused by tuples in the display
            if "," in rhs:
                return f"{latex(sympify(lhs))} = {rhs}"
            
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
        # --- PARSE PREVIOUS LINE (The "Truth") ---
        # Standard parsing for the starting equation
        if "=" in line_prev_str:
            lhs, rhs = line_prev_str.replace("^", "**").split("=")
            eq1 = Eq(sympify(lhs), sympify(rhs))
        else:
            eq1 = sympify(line_prev_str.replace("^", "**"))

        # Solve Line A to get the "Correct Set"
        sol1 = solve(eq1, x)
        correct_set = set(sol1)

        # --- PARSE CURRENT LINE (The "Student Input") ---
        # logic: If there is a comma, we treat it as a manual list of values
        user_set = set()
        
        # Pre-clean string
        clean_curr = line_curr_str.replace("^", "**")
        
        # Case A: User typed "+/-" (e.g. x = +/- 4)
        if "+/-" in clean_curr:
            parts = clean_curr.split("+/-")
            val = sympify(parts[1])
            user_set.add(val)
            user_set.add(-val)
            
        # Case B: User typed a list (e.g. x = 4, -4)
        elif "," in clean_curr:
            # We assume the format "x = 4, -4" or just "4, -4"
            if "=" in clean_curr:
                rhs = clean_curr.split("=")[1]
            else:
                rhs = clean_curr
            
            # Split by comma and sympify each part
            vals = rhs.split(",")
            for v in vals:
                user_set.add(sympify(v))
                
        # Case C: Standard Equation (e.g. x = 4)
        elif "=" in clean_curr:
            lhs, rhs = clean_curr.split("=")
            eq2 = Eq(sympify(lhs), sympify(rhs))
            sol2 = solve(eq2, x)
            user_set = set(sol2)
            
        else:
            # Just an expression?
            user_set = set() # Invalid state for this specific check

        # --- VERDICT ---
        
        # Check for empty input issues
        if not line_prev_str or not line_curr_str:
            return False, "Empty"

        # 1. Perfect Match
        if correct_set == user_set:
            return True, "Valid"
        
        # 2. Subset Match (Partial Credit)
        if user_set.issubset(correct_set) and len(user_set) > 0:
            return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

def diagnose_error(line_prev_str, line_curr_str):
    return "Check your math logic."

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v0.7", page_icon="🧮")
st.title("🧮 Step-Checker v0.7")
st.caption("Now supports comma lists: x = 4, -4")

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
k2.button("±", on_click=add_to_curr, args=("+/-",))
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
        st.write("You found one valid solution, but you missed the other root.")
    else:
        st.error("❌ **Logic Break**")
