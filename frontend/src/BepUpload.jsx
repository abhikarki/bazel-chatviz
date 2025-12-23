import {useState} from "react";


const API_BASE = import.meta.env.VITE_API_URL;

export default function BepUpload(){
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState("idle");
    const [fileId, setFileId] = useState(null);
    const [artifacts, setArtifacts] = useState(null);
    const [polling, setPolling] = useState(false);

    async function handleFileChange(e){
        setFile(e.target.files[0]);
    }

    async function handleUpload(){
        if(!file) return alert("Select a file first");

        try{
            setStatus("initializing");

            const initRes = await fetch(`${API_BASE}/upload/init`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    filename: file.name,
                    content_type: file.type || "application/octet-stream",
                    size: file.size,
                }),
            });

            if(!initRes.ok) throw new Error("Init upload failed");

            const {file_id, url, fields} = await initRes.json();
            setFileId(file_id);

            setStatus("uploading");


            const formData = new FormData();
            Object.entries(fields).forEach(([k, v]) => 
                formData.append(k,v )
            );
            formData.append("file", file);

            const s3Res = await fetch(url, {
                method: "POST",
                body: formData,
            });

            if(!s3Res.ok) throw new Error("S3 upload failed");

            setStatus("finalizing");

            const completeRes = await fetch(`${API_BASE}/upload/complete`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({file_id}),
            });

            const completeData = await completeRes.json();
            setStatus(completeData.status);

            if(completeData.status === "processing"){
                pollStatus(file_id);
            }
        }
        catch(err){
            console.error(err);
            setStatus("error");
        }
    }

    async function pollStatus(id){
        setPolling(true);
        
        const interval = setInterval(async () =>{
            try{
                const res = await fetch(`${API_BASE}/upload/status/${id}`);
                const data = await res.json();

                setStatus(data.status);

                if(data.status === "completed"){
                    clearInterval(interval);
                    setPolling(false);
                    await fetchArtifacts(id);
                }

                if(data.status === "failed"){
                    clearInterval(interval);
                    setPolling(false);
                }
            }
            catch(err){
                console.error(err);
                clearInterval(interval);
                setPolling(false);
                setStatus("error");
            }
        }, 2000);  // every 2s
    }

    async function fetchArtifacts(id) {
        const res = await fetch(`${API_BASE}/upload/artifacts/${id}`);
        if(!res.ok) throw new Error("Failed to fetch artifacts");
        
        const urls = await res.json();

        const [summary, graph, resourceUsage] = await Promise.all([
            fetch(urls.summary_url).then(r => r.json()),
            fetch(urls.graph_url).then(r => r.json()),
            fetch(urls.resource_usage_url).then(r => r.json()),
        ]);

        setArtifacts({summary, graph, resourceUsage});
    }

    return (
        <div>
            <h2>BEP file Upload</h2>

            <input type = "file" accept = ".json" onChange={handleFileChange} />
            <button onClick = {handleUpload}> Upload </button>

            <p>Status: {status}</p>
            {fileId && <p>File ID: {fileId}</p>}

            {artifacts && (
                <div>
                    <h3>Summary</h3>
                    <pre>{JSON.stringify(artifacts.summary, null, 2)}</pre>

                    <h3>Graph</h3>
                    <pre>{JSON.stringify(artifacts.graph, null, 2)}</pre>

                    <h3>Resource Usage</h3>
                    <pre>{JSON.stringify(artifacts.resourceUsage, null, 2)}</pre>
                </div>
            )} 
        </div>
    );
}
