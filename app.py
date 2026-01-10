import streamlit as st
import sympy
from sympy import symbols, sympify, solve, Eq, latex, N, reduce_inequalities
from sympy.core.numbers import Integer, Float, Rational
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
        if "±" in clean:
            parts = clean.split("±")
            val = smart_parse(parts[1].strip(), evaluate=True)
            return sympy.FiniteSet(val, -val)
        elif "," in clean:
            rhs = clean.split("=")[1] if "=" in clean else clean
            items = rhs.split(",")
            vals = []
            for i in items:
                if i.strip(): vals.append(smart_parse(i.strip(), evaluate=True))
            return sympy.FiniteSet(*vals)
        else:
            expr = smart_parse(clean, evaluate=True)
            if not isinstance(expr, Eq) and not expr.is_Relational:
                 if 'x' not in str(expr):
                     return sympy.FiniteSet(expr)
            if isinstance(expr, Eq) or not (expr.is_Relational):
                if not isinstance(expr, Eq): pass 
                sol = sympy.solve(expr, x, set=True)
                return sol[1] 
            else:
                solution = reduce_inequalities(expr, x)
                return solution.as_set()
    except Exception as e:
        return None

# --- NEW: SIMPLIFICATION CHECKER ---
def check_simplification(text):
    """
    Returns True if the expression is likely simplified (just a number).
    Returns False if it looks like unfinished math (10-4, 5*2, etc).
    """
    try:
        clean = clean_input(text)
        # Parse WITHOUT evaluating (keep 10-4 as 10-4, don't turn it into 6)
        expr = smart_parse(clean, evaluate=False)
        
        # If it's an equation x = 10-4, look at the Right Hand Side
        if isinstance(expr, Eq):
            rhs = expr.rhs
        else:
            rhs = expr
            
        # If the RHS is just a raw number (Integer, Float) or symbol (x), it's simplified.
        if rhs.is_Number or rhs.is_Symbol:
            return True
            
        # If it's a negative number like -6, SymPy sometimes treats it as Mul(-1, 6)
        # We need to allow that.
        if rhs.is_Mul and len(rhs.args) == 2 and rhs.args[0] == -1 and rhs.args[1].is_Number:
            return True
            
        # Otherwise, it involves an operation (Add, Mul, Pow) -> Unsimplified
        return False
    except:
        return True # Default to True if we can't tell, to avoid false alarms

# --- DIAGNOSTIC BRAIN v3.1 ---
def diagnose_error(set_correct, set_user):
    debug_log = []
    try:
        def extract_number(val):
            try: return float(val)
            except: pass
            try: return float(val[0])
            except: pass
            try: return float(val.args[0])
            except: pass
            return None

        c_vals = []
        try:
            for x in set_correct:
                val = extract_number(x)
                if val is not None: c_vals.append(val)
        except: return "Logic error.", "Iterate Fail"
        
        u_vals = []
        try:
            for x in set_user:
                val = extract_number(x)
                if val is not None: u_vals.append(val)
        except: return "Logic error.", "Iterate Fail"
            
        debug_log.append(f"Extracted A: {c_vals}")
        debug_log.append(f"Extracted B: {u_vals}")
        
        if not c_vals or not u_vals: 
            return "Check your values.", str(debug_log)

        c = c_vals[0]
        u = u_vals[0]

        if abs(u) == abs(c) and u != c:
            return "Check your signs (pos/neg).", str(debug_log)

        diff = u - c
        if 0 < abs(diff) <= 10:
            if abs(diff - round(diff)) < 0.001:
                return f"Close! You are off by {int(round(diff))}.", str(debug_log)
            else:
                return f"Close! You are off by {round(diff, 2)}.", str(debug_log)

        if c != 0 and abs(u - (1/c)) < 0.001:
            return "Did you flip the fraction?", str(debug_log)

        return "Logic error.", str(debug_log)

    except Exception as e:
        return f"Diagnostic Error: {e}", str(debug_log)


def validate_step(line_prev_str, line_curr_str):
    debug_info = {}
    try:
        if not line_prev_str or not line_curr_str: return False, "Empty", "", {}
        
        set_A = get_solution_set(line_prev_str)
        set_B = get_solution_set(line_curr_str)
        
        debug_info['Raw Set A'] = str(set_A)
        debug_info['Raw Set B'] = str(set_B)
        
        if set_A is None and line_prev_str: return False, "Could not solve Line A", "", debug_info
        if set_B is None: return False, "Could not parse Line B", "", debug_info

        # --- VALIDATION LOGIC ---
        if set_A == set_B:
            # NEW: Check if simplified!
            is_simple = check_simplification(line_curr_str)
            if is_simple:
                return True, "Valid", "", debug_info
            else:
                return True, "Unsimplified", "Mathematically correct, but simplify your answer.", debug_info

        hint, internal_debug = diagnose_error(set_A, set_B)
        debug_info['Internal X-Ray'] = internal_debug
        
        if "Check your" in hint or "Close!" in hint or "flip" in hint:
             pass
        elif set_B.is_subset(set_A) and not set_B.is_empty: 
             return True, "Partial", "", debug_info
        
        return False, "Invalid", hint, debug_info

    except Exception as e:
        return False, f"Syntax Error: {e}", "", debug_info

# --- WEB INTERFACE ---

st.set_page_config(page_title="The Logic Lab v3.3", page_icon="🧪")
st.title("🧪 The Logic Lab")

with st.sidebar:
    st.header("Settings")
    if st.session_state.history:
        st.write(f"Problems Checked: **{len(st.session_state.history)}**")
        df = pd.DataFrame(st.session_state.history)
        csv = convert_df_to_csv(df)
        st.download_button("📊 Download Session Data", csv, "Math_Session.csv", "text/csv")
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
    st.markdown("---")
    show_debug = st.checkbox("🛠️ Engineer Mode", value=False)

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
    elif is_valid and status == "Unsimplified":
        # NEW STATE: YELLOW WARNING
        st.warning("⚠️ **Correct, but not fully simplified.**")
        st.info("💡 **Hint:** Perform the arithmetic (e.g., 10-4).")
    elif is_valid and status == "Partial":
        st.warning("⚠️ **Technically Correct, but Incomplete.**")
    else:
        st.error("❌ **Logic Break**")
        if hint and hint != "Logic error.":
            st.info(f"💡 **Hint:** {hint}")
            
    if not is_valid and show_debug:
        st.markdown("---")
        st.write("🛠️ **Debug X-Ray:**")
        st.write(f"**Raw Set A:** `{debug_data.get('Raw Set A')}`")
        st.write(f"**Raw Set B:** `{debug_data.get('Raw Set B')}`")
        st.code(debug_data.get('Internal X-Ray'))

st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: #666;'><small>Built by The Logic Lab 🧪 | © 2026 Step-Checker</small></div>""",
    unsafe_allow_html=True
)
