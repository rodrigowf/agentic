/**
 * tool-workflow.integration.test.ts - Tool Management Workflow Integration Tests
 *
 * Tests complete tool management workflows including:
 * - Listing tools
 * - Uploading new tools
 * - Editing tool code
 * - Generating tool code with AI
 * - Saving tool modifications
 */

import { render, screen, fireEvent, waitFor, RenderResult } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { rest, RestRequest, ResponseComposition, RestContext } from 'msw';
import { server } from '../mocks/server';
import ToolsDashboard from '../../features/tools/pages/ToolsDashboard';
import { mockTools, mockToolCode } from '../mocks/data';

const API_URL = 'http://localhost:8000';

// Helper to render with router
const renderWithRouter = (component: React.ReactElement): RenderResult => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('Tool Workflow Integration Tests', () => {
  // ============================================================================
  // Tool List Workflow
  // ============================================================================

  describe('Tool List Workflow', () => {
    test('should load and display tool list', async () => {
      renderWithRouter(<ToolsDashboard />);

      // Wait for tools to load
      await waitFor(() => {
        expect(screen.getByText(/tools/i)).toBeInTheDocument();
      });

      // Verify mock tools are displayed
      await waitFor(() => {
        mockTools.forEach((tool) => {
          const elements = screen.queryAllByText(new RegExp(tool.name, 'i'));
          expect(elements.length).toBeGreaterThan(0);
        });
      });
    });

    test('should display tool descriptions', async () => {
      renderWithRouter(<ToolsDashboard />);

      await waitFor(() => {
        expect(
          screen.getByText(/search the web for information/i)
        ).toBeInTheDocument();
      });
    });

    test('should group tools by file', async () => {
      renderWithRouter(<ToolsDashboard />);

      await waitFor(() => {
        expect(screen.getByText(/research\.py/i)).toBeInTheDocument();
        expect(screen.getByText(/memory\.py/i)).toBeInTheDocument();
      });
    });

    test('should handle empty tool list', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.json({ tools: [] }));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      await waitFor(() => {
        const noToolsMessage = screen.queryByText(/no tools/i);
        expect(noToolsMessage).toBeInTheDocument();
      });
    });

    test('should handle tool list loading error', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(500), ctx.json({ error: 'Server error' }));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      await waitFor(() => {
        const errorMessage = screen.queryByText(/error.*loading.*tools/i);
        expect(errorMessage).toBeInTheDocument();
      });
    });

    test('should search/filter tools', async () => {
      renderWithRouter(<ToolsDashboard />);

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/search.*tools/i) as HTMLInputElement;
        fireEvent.change(searchInput, { target: { value: 'web' } });
      });

      // Verify only matching tools are shown
      await waitFor(() => {
        expect(screen.getByText(/web_search/i)).toBeInTheDocument();
        expect(screen.queryByText(/memory/i)).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Tool Upload Workflow
  // ============================================================================

  describe('Tool Upload Workflow', () => {
    test('should open upload tool dialog', async () => {
      renderWithRouter(<ToolsDashboard />);

      // Click upload button
      const uploadButton = await screen.findByRole('button', {
        name: /upload.*tool/i,
      });
      fireEvent.click(uploadButton);

      // Verify file input is displayed
      await waitFor(() => {
        expect(screen.getByLabelText(/select.*file/i)).toBeInTheDocument();
      });
    });

    test('should upload tool file successfully', async () => {
      server.use(
        rest.post(`${API_URL}/api/tools/upload`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool uploaded successfully' })
          );
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open upload dialog
      const uploadButton = await screen.findByRole('button', {
        name: /upload.*tool/i,
      });
      fireEvent.click(uploadButton);

      // Select file
      const fileInput = await screen.findByLabelText(/select.*file/i) as HTMLInputElement;
      const file = new File(['def my_tool():\n    pass'], 'my_tool.py', {
        type: 'text/x-python',
      });

      fireEvent.change(fileInput, { target: { files: [file] } });

      // Submit
      const submitButton = screen.getByRole('button', { name: /upload/i });
      fireEvent.click(submitButton);

      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/uploaded successfully/i)).toBeInTheDocument();
      });
    });

    test('should validate file type', async () => {
      renderWithRouter(<ToolsDashboard />);

      // Open upload dialog
      const uploadButton = await screen.findByRole('button', {
        name: /upload.*tool/i,
      });
      fireEvent.click(uploadButton);

      // Try to upload non-Python file
      const fileInput = await screen.findByLabelText(/select.*file/i) as HTMLInputElement;
      const file = new File(['console.log("test")'], 'test.js', {
        type: 'text/javascript',
      });

      fireEvent.change(fileInput, { target: { files: [file] } });

      // Verify validation error
      await waitFor(() => {
        expect(
          screen.getByText(/only python files.*allowed/i)
        ).toBeInTheDocument();
      });
    });

    test('should handle upload errors', async () => {
      server.use(
        rest.post(`${API_URL}/api/tools/upload`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(400),
            ctx.json({ error: 'Invalid tool format' })
          );
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Upload file
      const uploadButton = await screen.findByRole('button', {
        name: /upload.*tool/i,
      });
      fireEvent.click(uploadButton);

      const fileInput = await screen.findByLabelText(/select.*file/i) as HTMLInputElement;
      const file = new File(['invalid content'], 'bad_tool.py', {
        type: 'text/x-python',
      });

      fireEvent.change(fileInput, { target: { files: [file] } });

      const submitButton = screen.getByRole('button', { name: /upload/i });
      fireEvent.click(submitButton);

      // Verify error message
      await waitFor(() => {
        expect(screen.getByText(/invalid tool format/i)).toBeInTheDocument();
      });
    });

    test('should cancel upload operation', async () => {
      renderWithRouter(<ToolsDashboard />);

      // Open dialog
      const uploadButton = await screen.findByRole('button', {
        name: /upload.*tool/i,
      });
      fireEvent.click(uploadButton);

      // Cancel
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Verify dialog is closed
      await waitFor(() => {
        expect(
          screen.queryByLabelText(/select.*file/i)
        ).not.toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Tool Edit Workflow
  // ============================================================================

  describe('Tool Edit Workflow', () => {
    test('should open tool editor', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Click edit button
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Verify editor is displayed
      await waitFor(() => {
        expect(screen.getByText(/editor/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      });
    });

    test('should load tool code in editor', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open editor
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Verify code is loaded
      await waitFor(() => {
        expect(screen.getByText(/def web_search/)).toBeInTheDocument();
      });
    });

    test('should save tool code successfully', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        }),
        rest.put(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool saved successfully' })
          );
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open editor
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Modify code (Monaco editor will be mocked)
      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        fireEvent.change(editor, {
          target: { value: mockToolCode + '\n# Modified' },
        });
      });

      // Save
      const saveButton = screen.getByRole('button', { name: /save/i });
      fireEvent.click(saveButton);

      // Verify success
      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      });
    });

    test('should handle save errors', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        }),
        rest.put(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(400),
            ctx.json({ error: 'Invalid Python syntax' })
          );
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open editor and save
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /save/i });
        fireEvent.click(saveButton);
      });

      // Verify error
      await waitFor(() => {
        expect(screen.getByText(/invalid python syntax/i)).toBeInTheDocument();
      });
    });

    test('should close editor without saving', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open editor
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Close
      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      // Verify editor is closed
      await waitFor(() => {
        expect(screen.queryByText(/editor/i)).not.toBeInTheDocument();
      });
    });

    test('should warn about unsaved changes', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open editor
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        fireEvent.click(editButtons[0]);
      });

      // Make changes
      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        fireEvent.change(editor, {
          target: { value: mockToolCode + '\n# Changed' },
        });
      });

      // Try to close
      const closeButton = screen.getByRole('button', { name: /close/i });
      fireEvent.click(closeButton);

      // Verify warning
      await waitFor(() => {
        expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // AI Tool Generation Workflow
  // ============================================================================

  describe('AI Tool Generation Workflow', () => {
    test('should open AI generation dialog', async () => {
      renderWithRouter(<ToolsDashboard />);

      // Click generate button
      const generateButton = await screen.findByRole('button', {
        name: /generate.*ai/i,
      });
      fireEvent.click(generateButton);

      // Verify prompt input is displayed
      await waitFor(() => {
        expect(screen.getByLabelText(/describe.*tool/i)).toBeInTheDocument();
      });
    });

    test('should generate tool code from prompt', async () => {
      const generatedCode = `def ai_generated_tool():
    """AI generated tool"""
    pass`;

      server.use(
        rest.post(`${API_URL}/api/tools/generate`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(generatedCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Open generation dialog
      const generateButton = await screen.findByRole('button', {
        name: /generate.*ai/i,
      });
      fireEvent.click(generateButton);

      // Enter prompt
      await waitFor(() => {
        const promptInput = screen.getByLabelText(/describe.*tool/i) as HTMLInputElement;
        fireEvent.change(promptInput, {
          target: { value: 'Create a tool that sends emails' },
        });
      });

      // Generate
      const submitButton = screen.getByRole('button', { name: /generate/i });
      fireEvent.click(submitButton);

      // Verify generated code is displayed
      await waitFor(() => {
        expect(screen.getByText(/ai_generated_tool/)).toBeInTheDocument();
      });
    });

    test('should allow editing generated code before saving', async () => {
      const generatedCode = 'def generated():\n    pass';

      server.use(
        rest.post(`${API_URL}/api/tools/generate`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(generatedCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Generate code
      const generateButton = await screen.findByRole('button', {
        name: /generate.*ai/i,
      });
      fireEvent.click(generateButton);

      await waitFor(() => {
        const promptInput = screen.getByLabelText(/describe.*tool/i) as HTMLInputElement;
        fireEvent.change(promptInput, { target: { value: 'Test prompt' } });
      });

      const submitButton = screen.getByRole('button', { name: /generate/i });
      fireEvent.click(submitButton);

      // Edit generated code
      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        fireEvent.change(editor, {
          target: { value: generatedCode + '\n# Modified by user' },
        });
      });

      // Verify editor is editable
      expect(screen.getByTestId('monaco-editor')).not.toBeDisabled();
    });

    test('should handle generation errors', async () => {
      server.use(
        rest.post(`${API_URL}/api/tools/generate`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(500),
            ctx.json({ error: 'AI generation failed' })
          );
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Try to generate
      const generateButton = await screen.findByRole('button', {
        name: /generate.*ai/i,
      });
      fireEvent.click(generateButton);

      await waitFor(() => {
        const promptInput = screen.getByLabelText(/describe.*tool/i) as HTMLInputElement;
        fireEvent.change(promptInput, { target: { value: 'Test prompt' } });
      });

      const submitButton = screen.getByRole('button', { name: /generate/i });
      fireEvent.click(submitButton);

      // Verify error message
      await waitFor(() => {
        expect(screen.getByText(/generation failed/i)).toBeInTheDocument();
      });
    });

    test('should validate prompt input', async () => {
      renderWithRouter(<ToolsDashboard />);

      // Open dialog
      const generateButton = await screen.findByRole('button', {
        name: /generate.*ai/i,
      });
      fireEvent.click(generateButton);

      // Try to generate without prompt
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /generate/i });
        fireEvent.click(submitButton);
      });

      // Verify validation error
      await waitFor(() => {
        expect(screen.getByText(/prompt.*required/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Tool Documentation Workflow
  // ============================================================================

  describe('Tool Documentation Workflow', () => {
    test('should display tool documentation', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // Click info/docs button
      await waitFor(() => {
        const infoButtons = screen.getAllByRole('button', {
          name: /info|docs/i,
        });
        fireEvent.click(infoButtons[0]);
      });

      // Verify documentation is displayed
      await waitFor(() => {
        expect(
          screen.getByText(/search the web for information/i)
        ).toBeInTheDocument();
      });
    });

    test('should show tool parameters', async () => {
      server.use(
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(mockToolCode));
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // View tool details
      await waitFor(() => {
        const toolItems = screen.getAllByText(/web_search/i);
        fireEvent.click(toolItems[0]);
      });

      // Verify parameters are shown
      await waitFor(() => {
        expect(screen.getByText(/query/i)).toBeInTheDocument();
        expect(screen.getByText(/max_results/i)).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // Complete Tool Lifecycle Workflow
  // ============================================================================

  describe('Complete Tool Lifecycle', () => {
    test('should complete full tool lifecycle: create -> edit -> save -> use', async () => {
      const newToolCode = 'def new_tool():\n    return "test"';

      server.use(
        // Upload
        rest.post(`${API_URL}/api/tools/upload`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool uploaded successfully' })
          );
        }),
        // Load for editing
        rest.get(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(ctx.status(200), ctx.text(newToolCode));
        }),
        // Save
        rest.put(`${API_URL}/api/tools/content/:filename`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({ message: 'Tool saved successfully' })
          );
        }),
        // Refresh list
        rest.get(`${API_URL}/api/tools`, (req: RestRequest, res: ResponseComposition, ctx: RestContext) => {
          return res(
            ctx.status(200),
            ctx.json({
              tools: [
                ...mockTools,
                {
                  name: 'new_tool',
                  description: 'A new tool',
                  file: 'new_tool.py',
                },
              ],
            })
          );
        })
      );

      renderWithRouter(<ToolsDashboard />);

      // 1. Upload tool
      const uploadButton = await screen.findByRole('button', {
        name: /upload.*tool/i,
      });
      fireEvent.click(uploadButton);

      const fileInput = await screen.findByLabelText(/select.*file/i) as HTMLInputElement;
      const file = new File([newToolCode], 'new_tool.py', {
        type: 'text/x-python',
      });
      fireEvent.change(fileInput, { target: { files: [file] } });

      const submitButton = screen.getByRole('button', { name: /upload/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/uploaded successfully/i)).toBeInTheDocument();
      });

      // 2. Edit tool
      await waitFor(() => {
        const editButtons = screen.getAllByRole('button', { name: /edit/i });
        const lastEditButton = editButtons[editButtons.length - 1];
        fireEvent.click(lastEditButton);
      });

      // 3. Save modifications
      await waitFor(() => {
        const saveButton = screen.getByRole('button', { name: /save/i });
        fireEvent.click(saveButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      });

      // 4. Verify tool appears in list
      await waitFor(() => {
        expect(screen.getByText(/new_tool/)).toBeInTheDocument();
      });
    });
  });
});
