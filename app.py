import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, Tuple

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
        # Visual fix for +/-
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
            # 1. Handle "+/-" by expanding it manually
            # If user types "x = +/- 4", we treat it as the set {-4, 4}
            if "+/-" in eq_str:
                parts = eq_str.split("+/-")
                val = sympify(parts[1])
                # Return an equation equal to a Set of values {-val, val}
                # (Note: This is a hack to force 'solve' to see both values)
                return Eq(x**2, val**2) 
                
            # 2. Standard Parsing
            eq_str = eq_str.replace("^", "**") 
            
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
        
        # --- FLATTEN LOGIC (The Fix for '4, -4') ---
        # If sol2 looks like [(4, -4)], it's a tuple (coordinate).
        # We need to flatten it into [-4, 4]
        flat_sol2 = set()
        for item in sol2:
            if isinstance(item, Tuple):
                flat_sol2.update(item) # Break the coordinate apart
            else:
                flat_sol2.add(item)
        
        # Convert sol1 to set for comparison
        correct_set = set(sol1)
        
        # --- VERDICT ---
        
        # 1. Perfect Match (Sets are identical)
        if correct_set == flat_sol2:
            return True, "Valid"
        
        # 2. Subset Match (Partial Credit)
        if flat_sol2.issubset(correct_set) and len(flat_sol2) > 0:
            return True, "Partial"
            
        return False, "Invalid"

    except Exception as e:
        return False, f"Syntax Error: {e}"

def diagnose_error(line_prev_str, line_curr_str):
    return "Check your math logic."

# --- WEB INTERFACE ---

st.set_page_config(page_title="Step-Checker v0.6", page_icon="🧮")
st.title("🧮 Step-Checker v0.6")
st.caption("Now supports lists (4, -4) and +/- syntax")

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
k2.button("±", on_click=add_to_curr, args=("+/-",)) # Updated Button!
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
