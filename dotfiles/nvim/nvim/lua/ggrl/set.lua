-- Autor: Gabriel Góes Rocha de Lima
-- after/plugin/set.lua
-- Last Change: 2024-02-05 00:48
-- Configurações do nvim
vim.opt.encoding = 'utf-8'
vim.opt.fileencoding = 'utf-8'
vim.opt.guicursor = ""
vim.opt.nu = true
vim.opt.relativenumber = true
vim.opt.tabstop = 4
vim.opt.softtabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.hlsearch = false
vim.opt.incsearch = true
vim.opt.smartindent = true
vim.opt.wrap = false
vim.opt.termguicolors = true
vim.opt.scrolloff = 12
vim.opt.signcolumn = "yes"
vim.opt.isfname:append("@-@")
vim.opt.colorcolumn = "80"
vim.opt.clipboard = 'unnamedplus'
vim.opt.updatetime = 250
vim.g.mapleader = " "
vim.g.pymode_lint_signs = 0
-- Aumentar o espaço da primeira coluna antes dos linenumbers
vim.opt.numberwidth = 1
-- Aumentar o tamanho da primeira coluna.
vim.opt.foldcolumn = "1"
-- Aumentar o espaço disponível por caractere no signicons
vim.opt.signcolumn = "yes:1"
vim.opt.showcmd = true
vim.opt.cmdheight = 1
-- Configurações VIMdiagnostic
vim.api.nvim_create_autocmd({"CursorHold",
                             "CursorHoldI"},
    {callback = function()
        vim.diagnostic.open_float(nil, {
            focusable = false,
            close_events = {"BufLeave",
                            "CursorMoved",
                            "InsertEnter",
                            "FocusLost"},
            border = 'single',
            source = 'always',
            prefix = ' ',
            scope = 'cursor',
        })
    end,
})
vim.diagnostic.config({
    -- enable buffer diagnostics hover mouse
    float = {
        source = "true",
        preview = true,
        scope = "buffer",
    },
    signs = true,
    underline = true,
    update_in_insert = false,
    severity_sort = true
})
print("lua/ggrl/set.lua carregado com sucesso!")
