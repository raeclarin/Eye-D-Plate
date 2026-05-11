<!-- Consider the fact that one vehicle can have multiple owners -->


<script lang="ts">
    import { supabase } from '$lib/client';

    let plateInput = $state('');
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
    console.log('Click!');
    loading = true;
    message = '';
    matchedVehicle = null;

    const normalizedPlate = normalizePlate(plateInput);

    if (!normalizedPlate) {
        message = 'Please enter a plate number.';
        loading = false;
        return;
    }

    const { data, error } = await supabase
        .from('vehicles')
        .select('*')
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
        matchedVehicle = data;
        message = 'This plate is registered.';
    } else {
        console.log('Received data.');
        message = 'This plate is not registered.';
    }

    loading = false;
    }
</script>

<main style="max-width: 600px; margin: 3rem auto; font-family: sans-serif;">
    <h1><b>Eye-D-Plate</b></h1>

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
            <p><strong>Owner ID:</strong> {matchedVehicle.personnel_id}</p>
            <p><strong>Plate:</strong> {matchedVehicle.plate_number}</p>
            <p><strong>Vehicle Make:</strong> {matchedVehicle.make}</p>
            <p><strong>Vehicle Model:</strong> {matchedVehicle.model}</p>
            <p><strong>Color:</strong> {matchedVehicle.color}</p>
        </section>
    {/if}
</main>