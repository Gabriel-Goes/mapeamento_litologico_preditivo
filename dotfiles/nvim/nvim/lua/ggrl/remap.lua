-- Nvim remaps
vim.g.mapleader = " "
vim.keymap.set("n", "<leader>pv", "<cmd>Ex<CR>",
               { noremap = true, silent = true })
-- Copilot remaps
vim.g.copilot_no_tab_map=true
vim.api.nvim_set_keymap("i", "<C-J>", 'copilot#Accept("<CR>")',
                        { silent = true, expr = true })
-- Move line
vim.keymap.set("n", "<C-d>", "<C-d>zz")
vim.keymap.set("n", "<C-u>", "<C-u>zz")
vim.keymap.set("n", "n", "nzzzv")
vim.keymap.set("n", "N", "Nzzzv")
-- change buffers with Alt + j/k
vim.keymap.set("n", "<A-k>", "<cmd>bn<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<A-j>", "<cmd>bp<CR>", { noremap = true, silent = true })
-- Set all files at this dir into .md filetype
print("lua/ggrl/remap.lua carregado com sucesso!")
