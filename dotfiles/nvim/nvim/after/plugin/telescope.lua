-- Telescope
local builtin = require('telescope.builtin')
vim.keymap.set("n", "<leader>ff", builtin.find_files, {})
vim.keymap.set('n', '<leader>fb', builtin.buffers, {})
vim.keymap.set('n', '<leader>fh', builtin.help_tags, {})
vim.keymap.set("n", "<C-p>", builtin.git_files, {})
vim.keymap.set("n", "<leader>ps", function()
    builtin.grep_string({ search = vim.fn.input("Grep > ") });
end)
vim.keymap.set("n", "<leader>po", function()
    builtin.live_grep({ search = vim.fn.input("Live Grep > ")});
end)
vim.keymap.set("n", "<leader>gf", function()
    builtin.grep_string({ search = vim.fn.expand("<cword>") });
end)

require('telescope').setup{
    extensions = {
        live_grep = {
            prompt = 'Live Grep > ',
            input = '',
        },
        fzf = {
            fuzzy = true,                    -- false will only do exact matching
            override_generic_sorter = true,  -- override the generic sorter
            override_file_sorter = true,     -- override the file sorter
            case_mode = "smart_case",        -- or "ignore_case" or "respect_case"
        }
    }
}
require('telescope').load_extension('fzf')
