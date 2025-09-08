from flask import Flask, render_template_string
import botdiscord  # Assure-toi que botdiscord.py est importable

app = Flask(__name__)

@app.route("/")
def index():
    stats = botdiscord.COMMAND_STATS
    html = """
    <h1>Statistiques d'utilisation des commandes</h1>
    <table border="1">
        <tr><th>Commande</th><th>Utilisations</th></tr>
        {% for cmd, count in stats.items() %}
        <tr><td>{{ cmd }}</td><td>{{ count }}</td></tr>
        {% endfor %}
    </table>
    """
    return render_template_string(html, stats=stats)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)