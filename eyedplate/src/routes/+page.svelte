<!-- Consider the fact that one vehicle can have multiple owners -->
<script lang="ts">
    import { supabase } from '$lib/client';
    
    let imageSrc = $state('');
    let detections = $state('');

    const socket = new WebSocket("ws://localhost:8000/ws/stream");

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        imageSrc = data.image;

        if (data.detections[0]) {
            detections = data.detections[0].text;
            console.log(detections);
            checkPlate();
        };
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
    <h1><b>Eye-D-Plate</b></h1>

    
    {#if imageSrc}
        <img src={imageSrc} width="300" alt="qbb"/>
    {:else}
        <p>No image found.</p>
    {/if}

    {#if detections}
        <p><b>Last scanned plate: {detections}</b></p>
    {:else}
        <p>No plate found.</p>
    {/if}

    <!--

    <label for="plate">Enter a plate number.</label>

    <input
        id="plate"
        bind:value={plateInput}
        placeholder="Example: ABC 1234"
        style="display: block; width: 100%; padding: 0.75rem; margin: 0.5rem 0 1rem;"
    />

    <button onclick={checkPlate} disabled={loading}>
        {loading ? 'Checking...' : 'Check Plate'}
    </button>
    
    <br>    

    <br>
 -->
    <h1><b>Gate Open Status: {gateOpenState}</b></h1>

    <button onclick={openGate}>
        Open Gate
    </button>

    <br>

    <button onclick={closeGate}>
        Close Gate
    </button>

    {#if message}
        <p style="margin-top: 1.5rem; font-weight: bold;">
            {message}
        </p>
    {/if}

    {#if matchedVehicle}
        <section style="margin-top: 1rem; padding: 1rem; border: 1px solid #ccc;">
            
            <p><strong>Owner Name:</strong> {matchedVehicle.personnel?.first_name + " " + matchedVehicle.personnel?.last_name}</p>
            <p><strong>Owner ID:</strong> {matchedVehicle.personnel_id}</p>
            <p><strong>Department:</strong> {matchedVehicle.personnel?.department}</p>
            <p><strong>Rank:</strong> {matchedVehicle.personnel?.role}</p>
            <br>
            <p><strong>Plate:</strong> {matchedVehicle.plate_number}</p>
            <p><strong>Vehicle Type:</strong> {matchedVehicle.vehicle_type}</p>
            <p><strong>Vehicle Make:</strong> {matchedVehicle.make}</p>
            <p><strong>Vehicle Model:</strong> {matchedVehicle.model}</p>
            <p><strong>Color:</strong> {matchedVehicle.color}</p>
        </section>
    {/if}

    <button onclick={connectToArduino}>Connect Arduino via USB</button>
    <input type="text" bind:value={textToSend} />
    <button onclick={sendState}>Send State to Arduino</button>
</main>