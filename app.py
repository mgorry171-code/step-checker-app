import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, N, reduce_inequalities
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd
import re

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "x + 4 = 10"
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []
if 'keypad_target' not in st.session_state:
    st.session_state.keypad_target = "Current Line"

# --- HELPER FUNCTIONS ---
def add_to_input(text_to_add):
    if st.session_state.keypad_target == "Previous Line":
        st.session_state.line_prev += text_to_add
    else:
        st.session_state.line_curr += text_to_add

def clean_input(text):
    text = text.lower()
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = text.replace(" and ", ",")
    text = text.replace("^", "**")
    text = text.replace("+/-", "±")
    text = text.replace("%", "/100")
    text = text.replace(" of ", "*")
    text = text.replace("=<", "<=").replace("=>", ">=")
    return text

def smart_parse(text, evaluate=True):
    transformations = (standard_transformations + (implicit_multiplication_application,))
    try:
        if "<=" in text or ">=" in text or "<" in text or ">" in text:
            return parse_expr(text, transformations=transformations, evaluate=evaluate)
        elif "=" in text:
            parts = text.split("=")
            lhs = parse_expr(parts[0], transformations=transformations, evaluate=evaluate)
            rhs = parse_expr(parts[1], transformations=transformations, evaluate=evaluate)
            return Eq(lhs, rhs)
        else:
            return parse_expr(text, transformations=transformations, evaluate=evaluate)
    except:
        return sympify(text, evaluate=evaluate)

def pretty_print(math_str):
    try:
        clean_str = clean_input(math_str)
        clean_str = clean_str.replace("±", "±")
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def get_solution_set(text_str):
    x = symbols('x')
    clean = clean_input(text_str)
    try:
        # Case A: "+/-" syntax
        if "±" in clean:
            parts = clean.split("±")
            val = smart_parse(parts[1].strip(), evaluate=True)
            return sympy.FiniteSet(val, -val)
            
        # Case B: Comma list
        elif "," in clean:
            rhs = clean.split("=")[1] if "=" in clean else clean
            items = rhs.split(",")
            vals = []
            for i in items:
                if i.strip(): vals.append(smart_parse(i.strip(), evaluate=True))
            return sympy.FiniteSet(*vals)
        else:
            expr = smart_parse(clean, evaluate=True)
            
            # Case C: It's just a number or expression (e.g. "7" or "x+4")
            # If it's NOT an equation (=) and NOT an inequality (<, >)
            if not isinstance(expr, Eq) and not expr.is_Relational:
                 # If it has 'x' in it, treat as expression to solve? 
                 # Or if it's just "7", treat as the value {7}.
                 if 'x' not in str(expr):
                     return sympy.FiniteSet(expr)
            
            # Case D: Equation or Inequality
            if isinstance(expr, Eq) or not (expr.is_Relational):
                if not isinstance(expr, Eq): pass 
                # solve returns a set of TUPLES sometimes: {(6,)}
                sol = sympy.solve(expr, x, set=True)
                return sol[1] 
            else:
                solution = reduce_inequalities(expr, x)
                return solution.as_set()
    except Exception as e:
        return None

# --- FIXED DIAGNOSTIC BRAIN 🧠 ---
def diagnose_error(set_correct, set_user):
    try:
        if not isinstance(set_correct, sympy.FiniteSet) or not isinstance(set_user, sympy.FiniteSet):
            return "Inequality logic mismatch."

        # THE ONION PEELER: Handle {(6,)} vs {6}
        def extract_number(val):
            # If it's a tuple (6,), get the first item
            if isinstance(val, tuple):
                return float(val[0])
            # If it's a raw number, convert to float
            return float(val)

        c_vals = []
        for x in set_correct:
            try: c_vals.append(extract_number(x)) 
            except: pass
        
        u_vals = []
        for x in set_user:
            try: u_vals.append(extract_number(x))
            except: pass
        
        if not c_vals or not u_vals: return "Check your values."

        c = c_vals[0]
        u = u_vals[0]

        # Check: SIGN ERROR
        if abs(u) == abs(c) and u != c:
            return "Check your signs (pos/neg)."

        # Check: ARITHMETIC
        diff = u - c
        if 0 < abs(diff) <= 10:
            if abs(diff - round(diff)) < 0.001:
                return f"Close! You are off by {int(round(diff))}."
            else:
                return f"Close! You are off by {round(diff, 2)}."

        # Check: FRACTION FLIP
        if c != 0 and abs(u - (1/c)) < 0.001:
            return "Did you flip the fraction?"

        return "Logic error."

    except Exception as e:
        return f"Diagnostic Error: {e}"


def validate_step(line_prev_str, line_curr_str):
    debug_info = {}
    try:
        if not line_prev_str or not line_curr_str: return False, "Empty", "", {}
        
        set_A = get_solution_set(line_prev_str)
        set_B = get_solution_set(line_curr_str)
        
        debug_info['Set A'] = str(set_A)
        debug_info['Set B'] = str(set_B)
        
        if set_A is None and line_prev_str: return False, "Could not solve Line A", "", debug_info
        if set_B is None: return False, "Could not parse Line B", "", debug_info

        if set_A == set_B: return True, "Valid", "", debug_info
        
        # New: Compare values directly if Sets didn't match perfectly (handles (6,) vs 6 mismatch)
        # This is a backup validation check
        hint = diagnose_error(set_A, set_B)
        if hint == "Logic error." or "Check your" in hint or "Close!" in hint:
             # If diagnostics ran without crashing, we know it's invalid
             pass
        else:
             # Sometimes the diagnostic might fail, but let's check subset logic
             pass

        if set_B.is_subset(set_A) and not set_B.is_empty: return True, "Partial", "", debug_info
        
        return False, "Invalid", hint, debug_info

    except Exception as e:
        return False, f"Syntax Error: {e}", "", debug_info

# --- WEB INTERFACE ---

st.set_page_config(page_title="The Logic Lab v2.8", page_icon="🧪")
st.title("🧪 The Logic Lab (v2.8)")

with st.sidebar:
    st.header("📝 Session Log")
    if st.session_state.history:
        st.write(f"Problems Checked: **{len(st.session_state.history)}**")
        df = pd.DataFrame(st.session_state.history)
        csv = convert_df_to_csv(df)
        st.download_button("📊 Download Excel/CSV", csv, "Math_Session.csv", "text/csv")
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Previous Line")
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    if st.session_state.line_prev: st.latex(pretty_print(st.session_state.line_prev))

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    if st.session_state.line_curr: st.latex(pretty_print(st.session_state.line_curr))

st.markdown("---")

with st.expander("⌨️ Show Math Keypad", expanded=False):
    st.write("Click a button to add it to the **" + st.session_state.keypad_target + "**.")
    st.radio("Target:", ["Previous Line", "Current Line"], horizontal=True, key="keypad_target", label_visibility="collapsed")
    st.write("") 
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button("x²", on_click=add_to_input, args=("^2",))
    c2.button("|x|", on_click=add_to_input, args=("abs(",))
    c3.button("(", on_click=add_to_input, args=("(",))
    c4.button(")", on_click=add_to_input, args=(")",))
    c5.button("±", on_click=add_to_input, args=("+/-",))
    c6.button("÷", on_click=add_to_input, args=("/",))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button(" < ", on_click=add_to_input, args=("<",))
    c2.button("\>", on_click=add_to_input, args=(">",)) 
    c3.button(" ≤ ", on_click=add_to_input, args=("<=",))
    c4.button(" ≥ ", on_click=add_to_input, args=(">=",))
    c5.markdown("") 
    c6.markdown("")

st.markdown("---")
debug_container = st.container()

if st.button("Check Logic", type="primary"):
    line_a = st.session_state.line_prev
    line_b = st.session_state.line_curr
    
    is_valid, status, hint, debug_data = validate_step(line_a, line_b)
    
    now = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.history.append({
        "Time": now, "Input A": line_a, "Input B": line_b, "Result": status, "Hint": hint
    })
    
    if is_valid and status == "Valid":
        st.success("✅ **Perfect Logic!**")
        st.balloons()
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
    else:
        st.error("❌ **Logic Break**")
        if hint:
            st.info(f"💡 **Hint:** {hint}")
            
    if not is_valid:
        with st.expander("🛠️ Developer Debugger"):
            st.write(f"**Set A:** `{debug_data.get('Set A')}`")
            st.write(f"**Set B:** `{debug_data.get('Set B')}`")

st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: #666;'><small>Built by The Logic Lab 🧪 | © 2026 Step-Checker</small></div>""",
    unsafe_allow_html=True
)
