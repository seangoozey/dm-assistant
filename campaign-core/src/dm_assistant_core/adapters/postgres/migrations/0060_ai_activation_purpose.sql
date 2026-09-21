-- TKT-0124: AI activations become per-purpose. Every existing receipt was an
-- extraction activation (the registry's only purpose until now).
ALTER TABLE ai_configuration_activations
    ADD COLUMN purpose text NOT NULL DEFAULT 'extraction';
