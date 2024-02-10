-- Autor: Gabriel Góes Rocha de Lima
-- after/plugin/lsp.lua
-- Last Change: 2024-02-03 20:46
-- LSP Native
local lsp = require('lsp-zero')
lsp.setup()
-- LSP CLIENTS
-------------- Lua_lsp
require'lspconfig'.lua_ls.setup{
    settings = {
        filetypes = {'lua'},
        Lua = {
            diagnostics = {
                enable = true,
                disable = {"undefined-global"},
                globals = {'vim'},
            },
        },
    },
    on_attach = function(client,bufnr)
        vim.keymap.set("n","K", vim.lsp.buf.hover, {buffer=bufnr})
        vim.keymap.set("n","gd", vim.lsp.buf.definition, {buffer=bufnr})
    end
}
-------------- Pylsp
require'lspconfig'.pylsp.setup{
    cmd = {"/home/ggrl/.config/ambiente_geologico/bin/pylsp"},
    on_attach = function(client,bufnr)
    vim.keymap.set("n","K", vim.lsp.buf.hover, {buffer=bufnr})
    vim.keymap.set("n","gd", vim.lsp.buf.definition, {buffer=bufnr})
    end,
    settings = {
        pylsp = {
            plugins = {
                pycodestyle = {
                    enabled = true,
                    ignore = {'E501'},
                },
            },
        },
       diagnostics = {
           enable = true,
           disable = {"undefined-variable"},
           globals = {"vim"},
       },
    }
}
require'lspconfig'.ltex.setup{
    filetypes = {"tex", "bib", "markdown"},
    settings = {
        ltex = {
            language = "pt-BR",
            dictionary = {
                ["pt-BR"] = vim.fn.readfile(vim.fn.expand("/home/ggrl/.config/nvim/dictionary/pt-BR.dic")),
            },
            enabled = true,
        }
    },
    on_attach = function(client,bufnr)
        vim.keymap.set("n","K", vim.lsp.buf.hover, {buffer=bufnr})
        vim.keymap.set("n","gd", vim.lsp.buf.definition, {buffer=bufnr})
    end
}
require'lspconfig'.grammarly.setup{
    filetypes = {'markdown', 'tex'},
    autostart = false,
}
require'lspconfig'.marksman.setup{
    filetypes = {'markdown'},
    autostart = false,
}
-- Change diagnostic symbols in the sign column (gutter)
local signs = { Error = "󰅚",
                Warn = "󰀪",
                Hint = "󰌶",
                Info = "" }
for type, icon in pairs(signs) do
  local hl = "DiagnosticSign" .. type
  vim.fn.sign_define(hl, { text = icon,
                           texthl = hl,
                           numhl = "" })
end
print("LSP Carregado com sucesso")
