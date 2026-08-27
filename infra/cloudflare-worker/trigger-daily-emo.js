// Cloudflare Worker: innesca workflow_dispatch su daily.yml al posto (o in
// affiancamento) dello schedule: nativo di GitHub Actions, che il
// 27/08/2026 non è scattato all'orario previsto (mancato trigger dello
// scheduler GitHub, non un fallimento della pipeline). Vedi
// infra/cloudflare-worker/README.md per dove incollarlo e come
// configurarlo. Non viene eseguito da GitHub Actions: è uno script a sé,
// eseguito dal Cron Trigger di questo Worker su Cloudflare.
export default {
  async scheduled(event, env, ctx) {
    const response = await fetch(
      "https://api.github.com/repos/antoniopompozzi/emo/actions/workflows/daily.yml/dispatches",
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.GITHUB_PAT}`,
          "Accept": "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "emo-external-trigger"
        },
        body: JSON.stringify({ ref: "main" })
      }
    );
    if (!response.ok) {
      const text = await response.text();
      console.error(`workflow_dispatch fallita: ${response.status} ${text}`);
      throw new Error(`GitHub API ha risposto ${response.status}`);
    }
    console.log("Trigger esterno EMO inviato con successo");
  }
};
