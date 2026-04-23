window.QuizCraftConfig = Object.freeze({
  backendBaseUrl: "http://127.0.0.1:8000",
  timeouts: Object.freeze({
    health: 5000,
    upload: 30000,
    generate: 120000,
    quizEditor: 15000,
  }),
});
