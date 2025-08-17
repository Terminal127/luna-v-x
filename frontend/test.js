// client.js

async function callServer() {
  try {
    const response = await fetch("http://localhost:9000/");

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json(); // assumes your server returns JSON
    console.log("✅ Response from server:", data);
  } catch (error) {
    console.error("❌ Error:", error);
  }
}

callServer();
