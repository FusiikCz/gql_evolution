-- Ensure event invitation states table exists for new tree-type enum.
CREATE TABLE IF NOT EXISTS event_invitation_states (
    id UUID PRIMARY KEY,
    created TIMESTAMP DEFAULT now(),
    lastchange TIMESTAMP DEFAULT now(),
    createdby_id UUID,
    changedby_id UUID,
    rbacobject_id UUID,
    name TEXT NOT NULL,
    name_en TEXT,
    description TEXT,
    parent_id UUID,
    is_final BOOLEAN DEFAULT FALSE,
    CONSTRAINT event_invitation_states_parent_fk
        FOREIGN KEY (parent_id) REFERENCES event_invitation_states(id)
);

-- Backfill column on existing invitations table if missing.
ALTER TABLE IF EXISTS event_invitations_evolution
    ADD COLUMN IF NOT EXISTS state_id UUID;
