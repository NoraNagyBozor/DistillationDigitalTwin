"""Energy figures and model performance metrics for the research-question section of the report.

Reads the Aspen heat duties and enthalpies from the workbook (the notebook ignores
them) and the digital twin results from results/results_all_tabs.xlsx.
Writes results/energy_by_tab.xlsx and results/energy_vs_pressure.png, and prints the metrics.
Run from this folder, after a full notebook run:  .venv\\Scripts\\python rq_energy_analysis.py
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import load_workbook

WORKBOOK = "CfD distillation simulation 1 (2).xlsx"
CAL_S_TO_MW = 4.184e-6
ANTOINE = {"LOW": (6.87776, 1171.17, 224.408), "HIGH": (6.95719, 1424.255, 213.21)}  # as in the notebook
PRESSURES = (0.2, 0.5, 1.0, 2.0, 3.0)
FEED_STAGES = (1, 2, 3, 4, 5)


def psat(component, t_c):
    a, b, c = ANTOINE[component]
    return 10 ** (a - b / (c + t_c))


def tab_name(pressure, feed_stage):
    return f"{pressure:g}".replace(".", ",") + f",{feed_stage}"


def read_tab(ws, pressure, feed_stage):
    q_cond, q_reb = ws["K4"].value * CAL_S_TO_MW, ws["K8"].value * CAL_S_TO_MW
    h_feed, h_bot, h_top = (ws[c + "25"].value * CAL_S_TO_MW for c in "DEF")
    top, feed = ws["Q4"].value, ws["D29"].value
    t_top, t_bot = ws["I4"].value, ws["I8"].value
    purity_top = ws["J12"].value
    alpha = np.sqrt(psat("LOW", t_top) / psat("HIGH", t_top) * psat("LOW", t_bot) / psat("HIGH", t_bot))
    return {
        "tab": tab_name(pressure, feed_stage), "pressure_bar": pressure, "feed_stage": feed_stage,
        "T_top_C": t_top, "T_boiler_C": t_bot, "alpha_geomean": alpha,
        "Q_reboiler_MW": q_reb, "Q_condenser_MW": q_cond,
        "balance_error_pct_of_Qreb": 100 * (h_feed + q_reb + q_cond - h_top - h_bot) / q_reb,
        "reflux_ratio_mass": ws["U4"].value / top,
        "top_NHEX_%_aspen": 100 * purity_top,
        "kWh_per_kg_NHEX_top": 1000 * q_reb / (top * purity_top),
        "kWh_per_kg_feed": 1000 * q_reb / feed,
    }


def fit_metrics(aspen, model):
    """MAE, largest deviation and the fit of Gulyamov et al.: 1 - ||y - y_hat|| / ||y - y_mean||."""
    y, y_hat = np.asarray(aspen, float), np.asarray(model, float)
    error = y_hat - y
    return {"MAE": abs(error).mean(), "largest": abs(error).max(), "mean_error": error.mean(),
            "fit": 1 - np.linalg.norm(error) / np.linalg.norm(y - y.mean())}


def print_model_performance():
    summary = pd.read_excel("results/results_all_tabs.xlsx", sheet_name="summary")
    stages = pd.read_excel("results/results_all_tabs.xlsx", sheet_name="stages")
    for label, first_feed in (("all 25 tabs", 1), ("feed on stages 2 to 5", 2)):
        s, t = summary[summary["feed_stage"] >= first_feed], stages[stages["feed_stage"] >= first_feed]
        rows = {"top purity": fit_metrics(s["top_N-HEX_%_aspen"], s["top_N-HEX_%_model"]),
                "bottom purity": fit_metrics(s["bottom_EB_%_aspen"], s["bottom_EB_%_model"]),
                "top temperature": fit_metrics(t[t["stage"] == 1]["aspen_T_K"], t[t["stage"] == 1]["T_K"]),
                "boiler temperature": fit_metrics(t[t["stage"] == 5]["aspen_T_K"], t[t["stage"] == 5]["T_K"]),
                "stage liquid n-hexane": fit_metrics(t["aspen_liq_purity_LOW_%"], t["liq_purity_LOW_%"]),
                "stage temperature": fit_metrics(t["aspen_T_K"], t["T_K"])}
        print(f"\nModel against Aspen, {label}:\n{pd.DataFrame(rows).T.round(3)}")
    summary["top_error"] = summary["top_N-HEX_%_model"] - summary["top_N-HEX_%_aspen"]
    stages["x_error"] = stages["liq_purity_LOW_%"] - stages["aspen_liq_purity_LOW_%"]
    stages["T_error"] = stages["T_K"] - stages["aspen_T_K"]
    print("\nTop purity error per pressure:\n", summary.groupby("pressure_bar")["top_error"]
          .agg(mean_error="mean", MAE=lambda e: e.abs().mean()).round(2))
    print("\nStage errors:\n", stages.groupby("stage").agg(
        x_MAE=("x_error", lambda e: e.abs().mean()), T_MAE=("T_error", lambda e: e.abs().mean())).round(2))
    print("\nTabs within 1 point on top purity:", (summary["top_error"].abs() <= 1).sum())
    for feed_stage, tab in summary.groupby("feed_stage"):
        tab = tab.set_index("pressure_bar")
        drop = lambda col: tab.loc[0.2, col] - tab.loc[3.0, col]
        print(f"Feed stage {feed_stage}: top purity falls {drop('top_N-HEX_%_model'):.2f} (model) "
              f"against {drop('top_N-HEX_%_aspen'):.2f} (Aspen) from 0.2 to 3 bar")
    for pressure, tab in summary.groupby("pressure_bar"):
        ranks = [tab.sort_values(c, ascending=False)["feed_stage"].tolist() for c in ("top_N-HEX_%_aspen", "top_N-HEX_%_model")]
        print(f"{pressure:g} bar feed-stage ranking, Aspen {ranks[0]}, model {ranks[1]}")


def draw_line(ax, x, y, color, marker, style, label):
    ax.plot(x, y, marker=marker, ls=style, color=color, lw=2, ms=7, label=label,
            markeredgecolor="#fcfcfb", markeredgewidth=1.2, clip_on=False, zorder=3)


def style_axis(ax, title, ylabel):
    ax.set_xscale("log")
    ax.set_xticks(PRESSURES, [f"{p:g}" for p in PRESSURES])
    ax.minorticks_off()
    ax.set_xlabel("Column top pressure (bar, log scale)", color="#52514e")
    ax.set_ylabel(ylabel, color="#52514e")
    ax.set_title(title, color="#0b0b0b", fontsize=11, loc="left", fontweight="bold")
    ax.grid(axis="y", color="#e1e0d9", lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#52514e", length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.set_facecolor("#fcfcfb")


def main():
    wb = load_workbook(WORKBOOK, data_only=True)
    energy = pd.DataFrame([read_tab(wb[tab_name(p, f)], p, f) for p in PRESSURES for f in FEED_STAGES])

    twin = pd.read_excel("results/results_all_tabs.xlsx", sheet_name="summary")
    energy = energy.merge(twin[["tab", "top_N-HEX_%_model"]], on="tab")
    energy.to_excel("results/energy_by_tab.xlsx", index=False)

    pd.set_option("display.width", 220, "display.max_columns", 30)
    s3 = energy[energy["feed_stage"] == 3].sort_values("pressure_bar")
    print(s3.drop(columns=["tab", "feed_stage"]).round(3).to_string(index=False))
    print("Largest |energy balance error| over the 25 tabs (% of reboiler duty):",
          round(energy["balance_error_pct_of_Qreb"].abs().max(), 4))
    print("Reflux ratio range:", energy["reflux_ratio_mass"].min().round(4), energy["reflux_ratio_mass"].max().round(4))
    top_vapour = 4 * 3750 / 3600  # kg/s of vapour condensed with R = 3
    print("Effective latent heat at feed stage 3 (kJ/kg):", (1000 * s3["Q_condenser_MW"].abs() / top_vapour).round(1).tolist())
    print("(Qreb - |Qcond|) / Qreb:", ((s3["Q_reboiler_MW"] - s3["Q_condenser_MW"].abs()) / s3["Q_reboiler_MW"]).round(3).tolist())
    print_model_performance()

    plt.rcParams["font.family"] = ["Calibri", "DejaVu Sans"]
    plt.rcParams["font.size"] = 10
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.6, 3.5), facecolor="#fcfcfb")
    p = s3["pressure_bar"].values

    draw_line(left, p, s3["top_NHEX_%_aspen"], "#2a78d6", "o", "--", "Aspen")
    draw_line(left, p, s3["top_N-HEX_%_model"], "#eb6834", "s", "-", "Digital twin")
    style_axis(left, "Top product purity", "n-Hexane in top product (mass %)")
    left.set_ylim(86, 100)
    left.legend(frameon=False, loc="lower left")
    left.annotate(f"{s3['top_NHEX_%_aspen'].iloc[-1]:.1f}", (3, s3["top_NHEX_%_aspen"].iloc[-1]), xytext=(0, -16),
                  textcoords="offset points", ha="center", color="#52514e")
    left.annotate(f"{s3['top_N-HEX_%_model'].iloc[-1]:.1f}", (3, s3["top_N-HEX_%_model"].iloc[-1]), xytext=(0, 9),
                  textcoords="offset points", ha="center", color="#52514e")

    draw_line(right, p, s3["Q_reboiler_MW"], "#1baf7a", "o", "-", "Reboiler")
    draw_line(right, p, s3["Q_condenser_MW"].abs(), "#6250d6", "s", "-", "Condenser")
    style_axis(right, "Heat duties (Aspen only)", "Heat duty (MW)")
    right.set_ylim(0, 2.5)
    right.legend(frameon=False, loc="lower left")
    for col, off in (("Q_reboiler_MW", 8), ("Q_condenser_MW", -14)):
        for i in (0, -1):
            right.annotate(f"{abs(s3[col].iloc[i]):.2f}", (p[i], abs(s3[col].iloc[i])), xytext=(0, off),
                           textcoords="offset points", ha="left" if i == 0 else "right", color="#52514e")

    fig.tight_layout(w_pad=2.5)
    fig.savefig("results/energy_vs_pressure.png", dpi=200, facecolor=fig.get_facecolor())
    print("Saved results/energy_by_tab.xlsx and results/energy_vs_pressure.png")


if __name__ == "__main__":
    main()
