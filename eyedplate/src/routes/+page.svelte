<!-- Consider the fact that one vehicle can have multiple owners -->
<script lang="ts">
    import { supabase } from '$lib/client';
    
    let imageSrc = $state('');
    let detections = $state('');

    const socket = new WebSocket("ws://localhost:8000/ws/stream");

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // 1. Update the image stream
        if (data.image) {
            imageSrc = data.image;
        }

        // 2. Check for confirmed plate recognitions instead of 'detections'
        if (data.new_recognitions && data.new_recognitions.length > 0) {
            detections = data.new_recognitions[0].text;
            console.log("Confirmed plate:", detections);
            checkPlate();
        }
    };


    socket.onerror = (err) => {
        console.error("WebSocket error:", err);
    };

    socket.onclose = () => {
        console.log("WebSocket closed.");
    };

    let loading = $state(false);
    let message = $state('');
    let matchedVehicle: any = $state(null);
    let gateOpenState = $state(false);
    
    function openGate() {
        gateOpenState = true;
    }

    function closeGate() {
        gateOpenState = false;
    }

    function normalizePlate(plate: string) {
    return plate
        .toUpperCase()
        .replaceAll(' ', '')
        .replaceAll('-', '')
        .trim();
    }

    async function checkPlate() {
        console.log('Sent plate data.');
        loading = true;
        message = '';
        matchedVehicle = null;

        const normalizedPlate = normalizePlate(detections);

        const { data, error } = await supabase
            .from('vehicles')
            .select(`
                id,
                plate_number,
                normalized_plate_number,
                vehicle_type,
                make,
                model,
                color,
                status,
                personnel_id,
                personnel (
                  first_name,
                  last_name,
                  role,
                  department
                )
            `)
            .eq('normalized_plate_number', normalizedPlate)
            .eq('status', 'active')
            .maybeSingle();

        if (error) {
            console.log({ data, error });
            message = `Database error: ${error.message}`;
            loading = false;
            return;
        }

        if (data) {
            console.log('Received data.');
            console.log(data);
            matchedVehicle = data;
            message = 'This plate is registered.';
        } else {
            console.log('Received data.');
            message = 'This plate is not registered.';
        }

        loading = false;
    }

    // Async loop for Arduino

            
    let port: SerialPort | null = null;
    let textToSend = $state("LED_ON");

    async function connectToArduino() {
        try {
        // Prompt user to select the Arduino USB port
        port = await navigator.serial.requestPort();
        // Open the port at 9600 baud rate
        await port.open({ baudRate: 9600 });
        alert("Connected to Arduino!");
        } catch (error) {
        console.error("Connection failed:", error);
        }
    }

    async function sendState() {
        if (!port || !port.writable) {
        alert("Please connect to Arduino first!");
        return;
        }

        const encoder = new TextEncoder();
        const writer = port.writable.getWriter();
        
        // Add a newline character so Arduino knows the message ended
        const dataWithNewline = textToSend + "\n"; 
        
        await writer.write(encoder.encode(dataWithNewline));
        writer.releaseLock();
    }
</script>

<main style="max-width: 600px; margin: 3rem auto; font-family: sans-serif;">
    <h1 class="title">Eye-D-Plate</h1>

    <section class="card">
        <h2>Live Camera Feed</h2>

        {#if imageSrc}
            <img class="camera-feed" src={imageSrc} alt="Camera Feed" />
        {:else}
            <p class="muted">No image found.</p>
        {/if}
    </section>

    <section class="card">
        <h2>Detection Status</h2>

        {#if detections}
            <p class="plate">
                {detections}
            </p>
        {:else}
            <p class="muted">No plate detected.</p>
        {/if}

        <p class:open={gateOpenState} class:closed={!gateOpenState}>
            Gate Status:
            <strong>
                {gateOpenState ? 'OPEN' : 'CLOSED'}
            </strong>
        </p>
    </section>

    <section class="controls">
        <button class="primary" onclick={openGate}>
            Open Gate
        </button>

        <button class="danger" onclick={closeGate}>
            Close Gate
        </button>
    </section>

    {#if message}
        <section class="card">
            <p class="message">
                {message}
            </p>
        </section>
    {/if}

    {#if matchedVehicle}
        <section class="card">
            <h2>Registered Vehicle</h2>

            <div class="info-grid">
                <p><strong>Owner:</strong> {matchedVehicle.personnel?.first_name} {matchedVehicle.personnel?.last_name}</p>

                <p><strong>ID:</strong> {matchedVehicle.personnel_id}</p>

                <p><strong>Department:</strong> {matchedVehicle.personnel?.department}</p>

                <p><strong>Rank:</strong> {matchedVehicle.personnel?.role}</p>
                <p><strong>Plate:</strong> {matchedVehicle.plate_number}</p>

                <p><strong>Type:</strong> {matchedVehicle.vehicle_type}</p>
                <p><strong>Make:</strong> {matchedVehicle.make}</p>

                <p><strong>Model:</strong> {matchedVehicle.model}</p>

                <p><strong>Color:</strong> {matchedVehicle.color}</p>
            </div>
        </section>
    {/if}

    <section class="card">
        <h2>Arduino Control</h2>

        <div class="arduino-controls">
            <button class="secondary" onclick={connectToArduino}>
                Connect Arduino
            </button>

            <input
                type="text"
                bind:value={textToSend}
                placeholder="Send command..."
            />

            <button class="primary" onclick={sendState}>
                Send
            </button>
        </div>
    </section> 
</main>
<style>
    :global(body) {
        margin: 0;
        background: #f4f6f8;
        font-family:
            Inter,
            system-ui,
            sans-serif;
        color: #1f2937;
    }

    .container {
        max-width: 900px;
        margin: 2rem auto;
        padding: 1rem;
    }

    .title {
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 2rem;
        font-weight: 700;
    }

    .card {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow:
            0 4px 12px rgba(0,0,0,0.06);
    }

    .camera-feed {
        width: 100%;
        border-radius: 12px;
        margin-top: 1rem;
    }

    .muted {
        color: #6b7280;
    }

    .plate {
        font-size: 2rem;
        font-weight: bold;
        letter-spacing: 0.15rem;
        margin-top: 1rem;
    }

    .controls {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    button {
        border: none;
        border-radius: 12px;
        padding: 0.9rem 1.2rem;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;

        transition:
            transform 0.15s ease,
            opacity 0.15s ease;
    }

    button:hover {
        transform: translateY(-2px);
        opacity: 0.92;
    }

    .primary {
        background: #2563eb;
        color: white;
    }

    .danger {
        background: #dc2626;
        color: white;
    }

    .secondary {
        background: #374151;
        color: white;
    }

    .open {
        color: #16a34a;
    }

    .closed {
        color: #dc2626;
    }

    .message {
        font-size: 1.1rem;
        font-weight: 600;
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 0.75rem;
        margin-top: 1rem;
    }

    .arduino-controls {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 1rem;
    }

    input {
        flex: 1;
        min-width: 220px;

        padding: 0.9rem;
        border-radius: 12px;
        border: 1px solid #d1d5db;
        font-size: 1rem;
    }

    h2 {
        margin-top: 0;
        margin-bottom: 1rem;
    }
</style>