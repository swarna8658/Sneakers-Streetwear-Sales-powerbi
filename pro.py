# app.py
import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
import io

# ---------- Config ----------
st.set_page_config(page_title="Patient Registry", layout="wide")
st.title("🏥 Patient Data Entry & Registry")

CSV_FILE = "Patients_Data.csv"
EXCEL_FILE = "Patients_Data.xlsx"

# Expected columns and order
EXPECTED_COLS = [
    "Entry Date", "Doctor Name", "Area Code", "City",
    "Patient Name", "Mobile No", "Disease", "Goal Amount"
]

# ---------- Helpers ----------
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the DataFrame contains all expected columns in the right order."""
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df[c] = ""
    # ensure ordering
    return df[EXPECTED_COLS]

def load_data() -> pd.DataFrame:
    """Load CSV if exists, coerce date column to date objects, and ensure columns."""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        # parse date column safely
        if "Entry Date" in df.columns:
            try:
                df["Entry Date"] = pd.to_datetime(df["Entry Date"], errors="coerce").dt.date
            except Exception:
                pass
        df = ensure_columns(df)
        return df
    else:
        return pd.DataFrame(columns=EXPECTED_COLS)

def save_data(df: pd.DataFrame):
    """Save to CSV and attempt Excel (Excel may require openpyxl)."""
    df_to_save = df.copy()
    # convert Entry Date to ISO string for saving to CSV
    if "Entry Date" in df_to_save.columns:
        df_to_save["Entry Date"] = df_to_save["Entry Date"].apply(
            lambda v: v.isoformat() if isinstance(v, (date, datetime)) else v
        )
    df_to_save.to_csv(CSV_FILE, index=False)
    # Try writing Excel; don't crash the app if engine not available
    try:
        df.to_excel(EXCEL_FILE, index=False)
    except Exception:
        pass

def append_row(row_df: pd.DataFrame):
    df = load_data()
    df = pd.concat([df, row_df], ignore_index=True)
    save_data(df)
    return df

def valid_text(s: str) -> bool:
    return isinstance(s, str) and len(s.strip()) >= 3

def valid_mobile(s: str) -> bool:
    return isinstance(s, str) and s.isdigit() and len(s) == 10

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Return Excel file bytes for download (if openpyxl/pandas supports it)."""
    towrite = io.BytesIO()
    try:
        # Pandas will use openpyxl if available
        with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return towrite.getvalue()
    except Exception:
        # fallback: create a CSV bytes instead (Excel can open CSV)
        return df.to_csv(index=False).encode("utf-8")

# ---------- Styling: white background for inputs (including number inputs) ----------
st.markdown(
    """
<style>
/* Apply white background and black text to input fields, including numeric inputs */
input, textarea, select {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* Streamlit specific */
.stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
  background-color: #ffffff !important;
  color: #000000 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- Data Entry Form ----------
st.header("➕ Add New Patient Record")

with st.form("entry_form", clear_on_submit=False):
    entry_date = st.date_input("Entry Date (select a date)", value=date.today())

    col1, col2 = st.columns(2)
    with col1:
        dr_name = st.text_input("Doctor's Name")
        area_code = st.number_input("Area Code", min_value=0, step=1, value=0)
        city = st.text_input("City")
        patient_name = st.text_input("Patient's Name")
    with col2:
        mobile_no = st.text_input("Patient's Mobile No (10 digits)")
        disease = st.text_input("Disease")
        goal_amount = st.number_input("Goal Amount", min_value=0, step=1, value=0)

    submit = st.form_submit_button("💾 Save Record")

if submit:
    # Validate
    errors = []
    if not valid_text(dr_name):
        errors.append("Doctor's Name must be at least 3 characters.")
    if not isinstance(area_code, (int, float)):
        errors.append("Area Code must be numeric.")
    if not valid_text(city):
        errors.append("City must be at least 3 characters.")
    if not valid_text(patient_name):
        errors.append("Patient's Name must be at least 3 characters.")
    if not valid_mobile(str(mobile_no)):
        errors.append("Mobile number must be exactly 10 digits.")
    if not valid_text(disease):
        errors.append("Disease must be at least 3 characters.")
    if not isinstance(goal_amount, (int, float)):
        errors.append("Goal Amount must be numeric.")

    if errors:
        for e in errors:
            st.error(e)
        st.warning("Please correct the errors above. The form remains populated for correction.")
    else:
        new_row = pd.DataFrame({
            "Entry Date": [entry_date],
            "Doctor Name": [dr_name.strip()],
            "Area Code": [int(area_code)],
            "City": [city.strip()],
            "Patient Name": [patient_name.strip()],
            "Mobile No": [str(mobile_no).strip()],
            "Disease": [disease.strip()],
            "Goal Amount": [int(goal_amount)]
        })

        # Defensive duplicate detection
        df_existing = load_data()
        doctor_col = df_existing.get("Doctor Name", pd.Series([""] * len(df_existing))).astype(str)
        patient_col = df_existing.get("Patient Name", pd.Series([""] * len(df_existing))).astype(str)
        mobile_col = df_existing.get("Mobile No", pd.Series([""] * len(df_existing))).astype(str)

        mask_dup = (
            doctor_col.str.lower().eq(dr_name.strip().lower()) &
            patient_col.str.lower().eq(patient_name.strip().lower()) &
            mobile_col.eq(str(mobile_no).strip())
        )
        dup = df_existing[mask_dup]

        if not dup.empty:
            st.warning("⚠️ Potential duplicate(s) found:")
            st.dataframe(dup, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🗑 Delete duplicate(s) and save new record"):
                    df_existing = df_existing.drop(dup.index).reset_index(drop=True)
                    df_existing = pd.concat([df_existing, new_row], ignore_index=True)
                    save_data(df_existing)
                    st.success("Duplicate(s) removed and new record saved.")
            with c2:
                if st.button("✅ Save anyway (keep duplicates)"):
                    append_row(new_row)
                    st.success("Record saved (duplicates retained).")
            with c3:
                if st.button("❌ Cancel"):
                    st.info("Operation canceled. No data saved.")
        else:
            append_row(new_row)
            st.success("✅ Record saved successfully.")
            # show the saved row as confirmation
            st.dataframe(new_row, use_container_width=True)

# ---------- Registry display ----------
st.markdown("---")
st.subheader("📋 Patient Registry")

df = load_data()
if df.empty:
    st.info("No records found. Add records using the form above.")
else:
    # Show a reset-index version so users can refer to Row Index for deletion.
    df_display = df.reset_index().rename(columns={"index": "Row Index"})
    st.dataframe(df_display, use_container_width=True)

    # Deletion UI (select rows by Row Index)
    st.write("**Delete rows** — select one or more rows below and press Delete.")
    delete_rows = st.multiselect(
        "Pick Row Index to delete",
        options=df_display["Row Index"].tolist(),
        format_func=lambda r: f"{r} — {df.loc[r, 'Patient Name']} ({df.loc[r, 'Mobile No']})"
    )
    if delete_rows:
        if st.button("🗑 Delete selected rows"):
            df = df.drop(delete_rows).reset_index(drop=True)
            save_data(df)
            st.success(f"Deleted {len(delete_rows)} row(s).")
            # refresh display
            df_display = df.reset_index().rename(columns={"index": "Row Index"})
            st.dataframe(df_display, use_container_width=True)

# ---------- Sidebar: filters for every column and download buttons ----------
st.sidebar.header("🔎 Filters (apply to data)")
df_full = load_data()  # fresh load

# Start with full copy
filtered = df_full.copy()

# For each expected column, create an appropriate filter control
for col in EXPECTED_COLS:
    if col not in filtered.columns:
        continue
    non_null = filtered[col].dropna()
    if non_null.empty:
        continue

    # Date column -> date range filter
    if col == "Entry Date":
        # convert to datetime if possible
        try:
            dates = pd.to_datetime(filtered["Entry Date"], errors="coerce").dropna().dt.date
            if not dates.empty:
                min_d = dates.min()
                max_d = dates.max()
                date_range = st.sidebar.date_input(f"{col} range", value=(min_d, max_d))
                # date_input may return single date if only one date chosen
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    d0, d1 = date_range
                    filtered = filtered[
                        pd.to_datetime(filtered["Entry Date"], errors="coerce").dt.date.between(d0, d1)
                    ]
        except Exception:
            pass

    # Numeric column -> slider
    elif pd.api.types.is_numeric_dtype(non_null):
        try:
            min_val = float(non_null.min())
            max_val = float(non_null.max())
            if min_val < max_val:
                sel = st.sidebar.slider(f"{col}", min_value=min_val, max_value=max_val, value=(min_val, max_val))
                filtered = filtered[(filtered[col] >= sel[0]) & (filtered[col] <= sel[1])]
            else:
                # identical values: checkbox filter
                if st.sidebar.checkbox(f"Filter {col} == {min_val}", value=False):
                    filtered = filtered[filtered[col] == min_val]
        except Exception:
            pass

    # Object/text column -> multiselect
    else:
        opts = sorted(non_null.astype(str).unique())
        if len(opts) <= 50:
            sel = st.sidebar.multiselect(f"{col}", options=opts, default=opts)
            if sel:
                filtered = filtered[filtered[col].astype(str).isin(sel)]
        else:
            # too many unique values -> provide text filter
            txt = st.sidebar.text_input(f"Filter text in {col}")
            if txt:
                filtered = filtered[filtered[col].astype(str).str.contains(txt, case=False, na=False)]

# global text search across object columns
st.sidebar.markdown("---")
txt_search = st.sidebar.text_input("Global text search (any text column)")
if txt_search:
    mask = pd.Series(False, index=filtered.index)
    for c in filtered.select_dtypes(include=["object"]).columns:
        mask |= filtered[c].astype(str).str.contains(txt_search, case=False, na=False)
    filtered = filtered[mask]

# Download filtered CSV & Excel
st.sidebar.markdown("### Downloads")
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("⬇ Download filtered CSV", data=csv_bytes, file_name="patients_filtered.csv", mime="text/csv")

excel_bytes = df_to_excel_bytes(filtered)
st.sidebar.download_button("⬇ Download filtered Excel", data=excel_bytes, file_name="patients_filtered.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Download full / entire file buttons
st.sidebar.markdown("---")
st.sidebar.markdown("### Entire dataset download")
full_csv = df_full.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("⬇ Download full CSV", data=full_csv, file_name="patients_full.csv", mime="text/csv")

full_excel = df_to_excel_bytes(df_full)
st.sidebar.download_button("⬇ Download full Excel", data=full_excel, file_name="patients_full.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# show filtered results below the registry header
st.subheader("Filtered view (applies sidebar filters)")
st.write(f"Showing {len(filtered)} row(s) (of {len(df_full)} total)")
st.dataframe(filtered.reset_index(drop=True), use_container_width=True)
