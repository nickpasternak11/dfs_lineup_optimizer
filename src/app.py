from flask import Flask, jsonify, render_template, request

from lineup_optimizer import DFSLineupOptimizer
from utils import get_current_week

app = Flask(__name__, template_folder="../templates")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/optimize", methods=["POST"])
def optimize():
    data = request.json
    optimizer = DFSLineupOptimizer()

    lineups = []
    for weights in [(1, 0), (0.9, 0.1), (0.8, 0.2)]:
        lineup = optimizer.get_lineup_df(
            week=int(data.get("week") if data.get("week") else optimizer.current_week),
            dst=data.get("dst"),
            one_te=data.get("one_te"),
            use_avg_fpts=True if weights[1] > 0 else False,
            weights={"proj_fpts": weights[0], "avg_fpts": weights[1]},
        )
        lineups.append(lineup.to_dict(orient="records"))

    return jsonify(lineups)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
