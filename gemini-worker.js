export default {
  async fetch(request, env) {
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: cors });
    }

    if (request.method !== "POST") {
      return new Response("استخدم POST", {
        status: 405,
        headers: cors
      });
    }

    try {
      const body = await request.json();
      const question = body.question;

      if (!question) {
        return Response.json(
          { error: "اكتب سؤالك القانوني" },
          { status: 400, headers: cors }
        );
      }

      const response = await fetch(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-goog-api-key": env.GEMINI_API_KEY
          },
          body: JSON.stringify({
            systemInstruction: {
              parts: [{
                text: "أنت مساعد قانوني متخصص في القانون المصري. أجب باللغة العربية، واذكر رقم المادة والقانون عند التأكد منهما. لا تخترع نصوصاً قانونية، ونبه المستخدم إلى ضرورة مراجعة محامٍ."
              }]
            },
            contents: [{
              parts: [{ text: question }]
            }]
          })
        }
      );

      const data = await response.json();

      return Response.json(
        data,
        { status: response.status, headers: cors }
      );

    } catch (error) {
      return Response.json(
        { error: "حدث خطأ في معالجة السؤال" },
        { status: 500, headers: cors }
      );
    }
  }
};
