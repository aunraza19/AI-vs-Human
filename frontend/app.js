const lk = window.LivekitClient;

const state = {
  room: null,
  topics: [],
  selectedTopicId: null,
  selectedUserStance: "agree",
  selectedLanguage: "english",
  audioEls: new Map(),
  aiIdentity: null,
  aiSpeaking: false,
  isConnected: false,
  overlayMinimized: false,
};

const nameInput = document.getElementById("name-input");
const topicsGrid = document.getElementById("topics-grid");
const stanceGrid = document.getElementById("stance-grid");
const languageGrid = document.getElementById("language-grid");
const connectBtn = document.getElementById("connect-btn");
const disconnectBtn = document.getElementById("disconnect-btn");
const statusPill = document.getElementById("status-pill");
const activityLog = document.getElementById("activity-log");
const audioStage = document.getElementById("audio-stage");
const aiBackdrop = document.getElementById("ai-backdrop");
const aiWindow = document.getElementById("ai-window");
const aiWindowFrame = document.getElementById("ai-window-frame");
const aiWindowLabel = document.getElementById("ai-window-label");
const aiWindowHint = document.getElementById("ai-window-hint");

function appendLog(label, message) {
  const line = document.createElement("p");
  line.className = "log-line";
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${label}: ${message}`;
  activityLog.prepend(line);
}

function setStatus(text, mode) {
  statusPill.textContent = text;
  statusPill.className = `status-pill ${mode}`;
}

function setConnectedUi(connected) {
  connectBtn.disabled = connected;
  disconnectBtn.disabled = !connected;
}

function isAiIdentity(identity) {
  return typeof identity === "string" && identity.startsWith("agent-");
}

function applyAiSpeakingVisuals() {
  const visible = aiWindow.classList.contains("visible");
  const isSpeaking = visible && state.aiSpeaking;
  aiWindowFrame.classList.toggle("speaking", isSpeaking);
  if (visible) {
    aiWindowLabel.textContent = isSpeaking ? "AI Speaking" : "AI Listening";
  }
}

function setAiWindowVisible(visible) {
  aiBackdrop.classList.toggle("visible", visible);
  aiBackdrop.setAttribute("aria-hidden", visible ? "false" : "true");

  aiWindow.classList.toggle("visible", visible);
  aiWindow.setAttribute("aria-hidden", visible ? "false" : "true");

  aiWindowHint.textContent = state.overlayMinimized
    ? "Press Esc to restore overlay"
    : "Press Esc to minimize overlay";

  if (!visible) {
    aiWindowFrame.classList.remove("speaking");
    aiWindowLabel.textContent = state.overlayMinimized ? "AI Minimized" : "AI Ready";
    return;
  }

  applyAiSpeakingVisuals();
}

function updateAiOverlayVisibility() {
  setAiWindowVisible(state.isConnected && !state.overlayMinimized);
}

function setAiSpeaking(speaking) {
  state.aiSpeaking = speaking;
  applyAiSpeakingVisuals();
}

function registerAiParticipant(participant) {
  if (!participant || !isAiIdentity(participant.identity)) {
    return;
  }

  state.aiIdentity = participant.identity;
  if (participant.isSpeaking) {
    setAiSpeaking(true);
  }
}

function clearAiParticipant(participant) {
  if (!participant || !state.aiIdentity) {
    return;
  }

  if (participant.identity === state.aiIdentity) {
    state.aiIdentity = null;
    setAiSpeaking(false);
    aiWindowLabel.textContent = "AI Ready";
  }
}

function renderTopics(topics) {
  topicsGrid.innerHTML = "";
  topics.forEach((topic, index) => {
    const card = document.createElement("label");
    card.className = "topic-card";
    card.dataset.topicId = topic.topic_id;

    const radio = document.createElement("input");
    radio.className = "topic-radio";
    radio.type = "radio";
    radio.name = "topic";
    radio.value = topic.topic_id;

    if (index === 0) {
      radio.checked = true;
      card.classList.add("selected");
      state.selectedTopicId = topic.topic_id;
    }

    radio.addEventListener("change", () => {
      state.selectedTopicId = topic.topic_id;
      document
        .querySelectorAll(".topic-card")
        .forEach((item) => item.classList.toggle("selected", item.dataset.topicId === topic.topic_id));
    });

    const title = document.createElement("p");
    title.className = "topic-title";
    title.textContent = topic.title;

    const subtitle = document.createElement("p");
    subtitle.className = "topic-subtitle";
    subtitle.textContent = `${topic.persona} · AI takes the opposite side of your choice`;

    card.appendChild(radio);
    card.appendChild(title);
    card.appendChild(subtitle);
    topicsGrid.appendChild(card);
  });
}

function wireStanceSelection() {
  if (!stanceGrid) {
    return;
  }

  stanceGrid.querySelectorAll(".stance-card").forEach((card) => {
    const radio = card.querySelector("input[name='user-stance']");
    if (!radio) {
      return;
    }

    card.addEventListener("click", () => {
      radio.checked = true;
      state.selectedUserStance = radio.value;
      stanceGrid
        .querySelectorAll(".stance-card")
        .forEach((item) => item.classList.toggle("selected", item === card));
    });
  });
}

function wireLanguageSelection() {
  if (!languageGrid) {
    return;
  }

  languageGrid.querySelectorAll(".stance-card").forEach((card) => {
    const radio = card.querySelector("input[name='debate-language']");
    if (!radio) {
      return;
    }

    card.addEventListener("click", () => {
      radio.checked = true;
      state.selectedLanguage = radio.value;
      languageGrid
        .querySelectorAll(".stance-card")
        .forEach((item) => item.classList.toggle("selected", item === card));
    });
  });
}

async function loadTopics() {
  const response = await fetch("/topics");
  if (!response.ok) {
    throw new Error("Unable to load topics");
  }
  const data = await response.json();
  state.topics = data.topics ?? [];
  renderTopics(state.topics);
}

function wireRoomEvents(room) {
  room.on(lk.RoomEvent.ConnectionStateChanged, (connectionState) => {
    if (connectionState === lk.ConnectionState.Connected) {
      state.isConnected = true;
      state.overlayMinimized = false;
      setStatus("Live", "live");
      updateAiOverlayVisibility();
      appendLog("Session", "Connected to LiveKit room.");
      return;
    }

    if (
      connectionState === lk.ConnectionState.Connecting ||
      connectionState === lk.ConnectionState.Reconnecting
    ) {
      state.isConnected = false;
      setStatus("Connecting", "connecting");
      return;
    }

    state.isConnected = false;
    state.overlayMinimized = false;
    setStatus("Idle", "idle");
    updateAiOverlayVisibility();
  });

  room.on(lk.RoomEvent.TrackSubscribed, (track, publication, participant) => {
    if (track.kind !== lk.Track.Kind.Audio) {
      return;
    }

    const el = track.attach();
    el.autoplay = true;
    audioStage.appendChild(el);

    const trackId = publication.trackSid || track.sid;
    state.audioEls.set(trackId, el);
    registerAiParticipant(participant);
    appendLog("Audio", `AI voice connected (${participant.identity}).`);
  });

  room.on(lk.RoomEvent.TrackUnsubscribed, (track, publication) => {
    if (track.kind !== lk.Track.Kind.Audio) {
      return;
    }

    const trackId = publication.trackSid || track.sid;
    const el = state.audioEls.get(trackId);
    if (el) {
      el.remove();
      state.audioEls.delete(trackId);
    }
    appendLog("Audio", "AI voice track unsubscribed.");
  });

  room.on(lk.RoomEvent.ParticipantConnected, (participant) => {
    registerAiParticipant(participant);
    appendLog("Participant", `${participant.identity} joined.`);
  });

  room.on(lk.RoomEvent.ParticipantDisconnected, (participant) => {
    clearAiParticipant(participant);
    appendLog("Participant", `${participant.identity} left.`);
  });

  room.on(lk.RoomEvent.ActiveSpeakersChanged, (speakers) => {
    const activeAi = speakers.find((participant) =>
      state.aiIdentity
        ? participant.identity === state.aiIdentity
        : isAiIdentity(participant.identity)
    );

    if (activeAi && !state.aiIdentity) {
      state.aiIdentity = activeAi.identity;
    }
    setAiSpeaking(Boolean(activeAi));
  });

  if (lk.RoomEvent.TranscriptionReceived) {
    room.on(lk.RoomEvent.TranscriptionReceived, (segments, participant) => {
      segments.forEach((segment) => {
        const isFinal = segment.final ?? segment.isFinal ?? true;
        if (!isFinal || !segment.text) {
          return;
        }
        appendLog(participant?.identity ?? "Transcript", segment.text);
      });
    });
  }

  room.on(lk.RoomEvent.Disconnected, () => {
    appendLog("Session", "Disconnected.");
    state.isConnected = false;
    state.overlayMinimized = false;
    setStatus("Idle", "idle");
    setConnectedUi(false);
    updateAiOverlayVisibility();
    state.aiIdentity = null;
    state.aiSpeaking = false;
    state.room = null;
  });
}

async function connectSession() {
  if (!state.selectedTopicId) {
    setStatus("Choose a topic", "error");
    return;
  }

  const name = nameInput.value.trim();
  if (!name) {
    setStatus("Enter your name", "error");
    return;
  }

  if (!state.selectedUserStance) {
    setStatus("Select your position", "error");
    return;
  }

  if (!state.selectedLanguage) {
    setStatus("Select language", "error");
    return;
  }

  connectBtn.disabled = true;
  setStatus("Connecting", "connecting");

  try {
    const response = await fetch("/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        topic_id: state.selectedTopicId,
        user_stance: state.selectedUserStance,
        language: state.selectedLanguage,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Unable to create token");
    }

    const tokenPayload = await response.json();
    const room = new lk.Room({
      adaptiveStream: true,
      dynacast: true,
      audioCaptureDefaults: {
        autoGainControl: true,
        echoCancellation: true,
        noiseSuppression: true,
        channelCount: 1,
        sampleRate: 16000,
      },
    });

    wireRoomEvents(room);
    await room.connect(tokenPayload.livekit_url, tokenPayload.token);
    await room.localParticipant.setMicrophoneEnabled(true);

    state.room = room;
    state.isConnected = true;
    state.overlayMinimized = false;
    setConnectedUi(true);
    updateAiOverlayVisibility();
    appendLog("Session", `Debate started in room ${tokenPayload.room_name}.`);
  } catch (error) {
    setStatus("Connection failed", "error");
    setConnectedUi(false);
    appendLog("Error", error instanceof Error ? error.message : "Unknown error");
  } finally {
    if (!state.room) {
      connectBtn.disabled = false;
    }
  }
}

async function disconnectSession() {
  if (!state.room) {
    return;
  }

  await state.room.disconnect();
  state.audioEls.forEach((el) => el.remove());
  state.audioEls.clear();
  state.room = null;
  state.aiIdentity = null;
  state.aiSpeaking = false;
  state.isConnected = false;
  state.overlayMinimized = false;

  setConnectedUi(false);
  setStatus("Idle", "idle");
  updateAiOverlayVisibility();
  appendLog("Session", "Session closed.");
}

connectBtn.addEventListener("click", connectSession);
disconnectBtn.addEventListener("click", disconnectSession);

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || event.repeat || !state.isConnected) {
    return;
  }

  state.overlayMinimized = !state.overlayMinimized;
  updateAiOverlayVisibility();
  appendLog(
    "Overlay",
    state.overlayMinimized
      ? "AI overlay minimized (press Esc to restore)."
      : "AI overlay restored."
  );
});

wireStanceSelection();
wireLanguageSelection();

loadTopics()
  .then(() => appendLog("Ready", "Enter your name, pick a topic, and start the debate."))
  .catch((error) => {
    setStatus("Load error", "error");
    appendLog("Error", error instanceof Error ? error.message : "Failed to initialize.");
  });
