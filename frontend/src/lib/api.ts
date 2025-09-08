export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	try {
		const res = await fetch(`${API_BASE}${path}`, {
			...options,
			headers: {
				"Content-Type": "application/json",
				...(options?.headers || {}),
			},
			// Add SSL handling for development
			...(process.env.NODE_ENV === 'development' && {
				// For development, we can be more lenient with SSL
			})
		});
		
		if (!res.ok) {
			const txt = await res.text();
			throw new Error(`HTTP ${res.status}: ${txt}`);
		}
		return (await res.json()) as T;
	} catch (error) {
		// Handle SSL certificate errors specifically
		if (error instanceof TypeError && error.message.includes('certificate')) {
			throw new Error(`SSL Certificate Error: ${error.message}. Try running with NODE_TLS_REJECT_UNAUTHORIZED=0 for development.`);
		}
		throw error;
	}
}

export const api = {
	health: () => request<{ status: string }>("/health"),
	dbStatus: () => request<{ status: string; error?: string; method?: string }>("/db/status"),
	dbConfig: () => request<{ host: string; port: string; database: string; user: string; password_set: boolean; dotenv_loaded: boolean }>("/db/config"),
	filters: (useDatabase: boolean = true) => {
		const endpoint = useDatabase ? "/filters" : "/csv/filters";
		return request<{ [k: string]: unknown }>(endpoint);
	},
	data: (body: unknown, useDatabase: boolean = true) => {
		const endpoint = useDatabase ? "/data" : "/csv/data";
		return request<{ rows: unknown[]; columns: string[]; summary?: any; source?: string; error?: string }>(endpoint, { method: "POST", body: JSON.stringify(body) });
	},
	composites: (body: unknown, useDatabase: boolean = true) => {
		const endpoint = useDatabase ? "/composites" : "/csv/composites";
		return request<{ series: unknown[]; metadata?: any; source?: string; error?: string }>(endpoint, { method: "POST", body: JSON.stringify(body) });
	},
	cappedAnalysis: (body: unknown) => {
		return request<{ analysis_results: unknown[]; output_file: string; parameters: any; source: string; record_count: number; error?: string }>("/analysis/capped-vs-uncapped", { method: "POST", body: JSON.stringify(body) });
	},
};
