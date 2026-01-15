import streamlit as st
import sympy
from sympy import symbols, solve, Eq, latex, simplify
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import datetime
import pandas as pd
import re
import numpy as np
import plotly.graph_objects as go # The Interactive Graphing Tool

# --- SETUP SESSION STATE ---
if 'line_prev' not in st.session_state:
    st.session_state.line_prev = "2x + 3y = 20; x + y = 8" 
if 'line_curr' not in st.session_state:
    st.session_state.line_curr = ""
if 'history' not in st.session_state:
    st.session_state.history = []
if 'keypad_target' not in st.session_state:
    st.session_state.keypad_target = "Current Line"
if 'step_verified' not in st.session_state:
    st.session_state.step_verified = False

# --- HELPER FUNCTIONS ---
def add_to_input(text_to_add):
    if st.session_state.keypad_target == "Previous Line":
        st.session_state.line_prev += text_to_add
    else:
        st.session_state.line_curr += text_to_add

def clean_input(text):
    text = text.lower()
    text = re.sub(r'(\d),(\d{3})', r'\1\2', text)
    text = text.replace(" and ", ";")
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
        if ";" in clean_str:
             parts = clean_str.split(";")
             latex_parts = [latex(smart_parse(p, evaluate=False)) for p in parts if p.strip()]
             return ", \\quad ".join(latex_parts)
        expr = smart_parse(clean_str, evaluate=False)
        return latex(expr)
    except:
        return None

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- LOGIC BRAIN 4.3 ---
def get_solution_set(text_str):
    x, y = symbols('x y')
    clean = clean_input(text_str)
    try:
        equations = []
        if ";" in clean:
            raw_eqs = clean.split(";")
            for r in raw_eqs:
                if r.strip(): equations.append(smart_parse(r, evaluate=True))
        elif clean.count("=") > 1 and "," in clean:
            raw_eqs = clean.split(",")
            for r in raw_eqs:
                if r.strip(): equations.append(smart_parse(r, evaluate=True))
        else:
             equations.append(smart_parse(clean, evaluate=True))

        if len(equations) > 1:
            sol = solve(equations, (x, y), set=True)
            return sol[1] 
        else:
            expr = equations[0]
            if isinstance(expr, tuple): return sympy.FiniteSet(expr)
            if isinstance(expr, Eq) or not (expr.is_Relational):
                 if 'y' in str(expr): return sympy.FiniteSet(expr)
                 else:
                     if 'x' not in str(expr) and 'y' not in str(expr): return sympy.FiniteSet(expr)
                     sol = solve(expr, x, set=True)
                     return sol[1] 
            else:
                solution = reduce_inequalities(expr, x)
                return solution.as_set()
    except Exception as e:
        return None

def check_simplification(text):
    try:
        clean = clean_input(text)
        expr = smart_parse(clean, evaluate=False)
        if isinstance(expr, Eq): rhs = expr.rhs
        else: rhs = expr
        if rhs.is_Number or rhs.is_Symbol: return True
        if rhs.is_Mul and len(rhs.args) == 2 and rhs.args[0] == -1 and rhs.args[1].is_Number: return True
        return False
    except:
        return True

def diagnose_error(set_correct, set_user):
    return "Check your math logic.", ""

def next_step():
    st.session_state.line_prev = st.session_state.line_curr
    st.session_state.line_curr = ""
    st.session_state.step_verified = False

# --- NEW: INTERACTIVE PLOTLY ENGINE 📉 ---
def plot_system_interactive(text_str):
    """
    Creates an interactive Plotly chart with hover info and a data table.
    """
    try:
        x, y = symbols('x y')
        clean = clean_input(text_str)
        
        equations = []
        if ";" in clean:
            raw_eqs = clean.split(";")
            for r in raw_eqs:
                if r.strip(): equations.append(smart_parse(r, evaluate=True))
        else:
            if clean.count("=") > 1 and "," in clean:
                 raw_eqs = clean.split(",")
                 for r in raw_eqs:
                    if r.strip(): equations.append(smart_parse(r, evaluate=True))
            else:
                 equations.append(smart_parse(clean, evaluate=True))
        
        # Create Plotly Figure
        fig = go.Figure()
        
        # Domain for plotting
        x_vals = np.linspace(-10, 10, 100)
        
        colors = ['blue', 'orange', 'green']
        i = 0
        point_data = [] # Store points for the table
        
        has_plotted = False
        
        for eq in equations:
            try:
                # SOLVE FOR Y
                if 'y' in str(eq):
                    y_expr = solve(eq, y)
                    if y_expr:
                        # Create Python function
                        f_y = sympy.lambdify(x, y_expr[0], "numpy")
                        y_vals = f_y(x_vals)
                        
                        # Add Line Trace
                        label = f"${latex(eq)}$"
                        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=f"Eq {i+1}", line=dict(color=colors[i % 3])))
                        
                        # Calculate a few nice integer points for the table (The "Guide")
                        table_points = []
                        for val in [-2, 0, 2, 4]:
                            try:
                                res_y = float(y_expr[0].subs(x, val))
                                table_points.append(f"({val}, {round(res_y, 2)})")
                            except: pass
                        
                        point_data.append({"Equation": f"Eq {i+1}", "Points to Plot": ", ".join(table_points)})

                        has_plotted = True
                        i += 1
                        
                # SOLVE FOR X (Vertical Line)
                elif 'x' in str(eq):
                    x_sol = solve(eq, x)
                    if x_sol:
                        val = float(x_sol[0])
                        fig.add_vline(x=val, line_dash="dash", line_color=colors[i%3], annotation_text=f"x={val}")
                        has_plotted = True
                        i += 1

            except: pass
        
        # Add Intersection Point Highlight if it's a system
        if len(equations) > 1:
            try:
                sol = solve(equations, (x, y))
                if sol and isinstance(sol, dict):
                    # Single intersection
                    sx = float(sol[x])
                    sy = float(sol[y])
                    fig.add_trace(go.Scatter(
                        x=[sx], y=[sy], 
                        mode='markers+text', 
                        marker=dict(size=12, color='red'),
                        text=[f"Intersection ({round(sx,1)}, {round(sy,1)})"],
                        textposition="top center",
                        name="Solution"
                    ))
            except: pass

        if not has_plotted: return None, None

        # Layout styling
        fig.update_layout(
            title="Interactive Graph (Zoom & Hover)",
            xaxis_title="X Axis",
            yaxis_title="Y Axis",
            xaxis=dict(range=[-10, 10], showgrid=True, zeroline=True, zerolinewidth=2, zerolinecolor='black'),
            yaxis=dict(range=[-10, 10], showgrid=True, zeroline=True, zerolinewidth=2, zerolinecolor='black'),
            height=500,
            showlegend=True
        )
        
        return fig, point_data

    except Exception as e:
        return None, None

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

        if set_A == set_B:
            return True, "Valid", "", debug_info
        
        hint, internal_debug = diagnose_error(set_A, set_B)
        return False, "Invalid", hint, debug_info

    except Exception as e:
        return False, f"Syntax Error: {e}", "", debug_info

# --- WEB INTERFACE ---

st.set_page_config(page_title="The Logic Lab v4.3", page_icon="🧪")
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

# --- DISPLAY AREA ---
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Previous Line")
    st.text_input("Line A", key="line_prev", label_visibility="collapsed")
    if st.session_state.line_prev: 
        st.latex(pretty_print(st.session_state.line_prev))
        
        # GRAPH SECTION (TABS)
        if st.checkbox("📈 Visualize Graph"):
            fig, data_points = plot_system_interactive(st.session_state.line_prev)
            if fig:
                tab1, tab2 = st.tabs(["📉 Interactive Graph", "🔢 Table of Points"])
                with tab1:
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("Hover over lines to see coordinates. Scroll to zoom.")
                with tab2:
                    st.write("**Guide Points:** Use these points to help plot the lines.")
                    if data_points:
                        st.table(pd.DataFrame(data_points))
            else:
                st.caption("Could not graph this expression.")

    st.caption("For Systems: Use ';' to separate. (e.g. `2x+y=10; x-y=4`)")

with col2:
    st.markdown("### Current Line")
    st.text_input("Line B", key="line_curr", label_visibility="collapsed")
    if st.session_state.line_curr: st.latex(pretty_print(st.session_state.line_curr))

st.markdown("---")

# --- KEYPAD ---
with st.expander("⌨️ Show Math Keypad", expanded=False):
    st.write("Click a button to add it to the **" + st.session_state.keypad_target + "**.")
    st.radio("Target:", ["Previous Line", "Current Line"], horizontal=True, key="keypad_target", label_visibility="collapsed")
    st.write("") 
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button("x²", on_click=add_to_input, args=("^2",))
    c2.button("|x|", on_click=add_to_input, args=("abs(",))
    c3.button("(", on_click=add_to_input, args=("(",))
    c4.button(")", on_click=add_to_input, args=(")",))
    c5.button(";", on_click=add_to_input, args=("; ",))
    c6.button("÷", on_click=add_to_input, args=("/",))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.button(" < ", on_click=add_to_input, args=("<",))
    c2.button("\>", on_click=add_to_input, args=(">",)) 
    c3.button(" ≤ ", on_click=add_to_input, args=("<=",))
    c4.button(" ≥ ", on_click=add_to_input, args=(">=",))
    c5.button("x", on_click=add_to_input, args=("x",))
    c6.button("y", on_click=add_to_input, args=("y",))

st.markdown("---")

# --- CHECK LOGIC & NEXT STEP ---
c_check, c_next = st.columns([1, 1])

with c_check:
    if st.button("Check Logic", type="primary"):
        line_a = st.session_state.line_prev
        line_b = st.session_state.line_curr
        
        is_valid, status, hint, debug_data = validate_step(line_a, line_b)
        
        now = datetime.datetime.now().strftime("%H:%M:%S")
        st.session_state.history.append({
            "Time": now, "Input A": line_a, "Input B": line_b, "Result": status, "Hint": hint
        })
        
        if is_valid:
            st.session_state.step_verified = True 
            if status == "Valid":
                st.success("✅ **Perfect Logic!**")
                st.balloons()
            elif status == "Unsimplified":
                st.warning("⚠️ **Correct, but not fully simplified.**")
                st.info("💡 **Hint:** Perform the arithmetic.")
            elif status == "Partial":
                st.warning("⚠️ **Technically Correct, but Incomplete.**")
        else:
            st.session_state.step_verified = False
            st.error("❌ **Logic Break**")
            if hint and hint != "Logic error.":
                st.info(f"💡 **Hint:** {hint}")
                
        if not is_valid and show_debug:
            st.markdown("---")
            st.write("🛠️ **Debug X-Ray:**")
            st.write(f"**Raw Set A:** `{debug_data.get('Raw Set A')}`")
            st.write(f"**Raw Set B:** `{debug_data.get('Raw Set B')}`")

with c_next:
    if st.session_state.step_verified:
        st.button("⬇️ Next Step (Move Down)", on_click=next_step)

st.markdown("---")
st.markdown(
    """<div style='text-align: center; color: #666;'><small>Built by The Logic Lab 🧪 | © 2026 Step-Checker</small></div>""",
    unsafe_allow_html=True
)
