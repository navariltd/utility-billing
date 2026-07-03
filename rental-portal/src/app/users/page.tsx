"use client";

import { BaseLayout } from "@/components/layouts/base-layout";
import { useUser } from "@/contexts/user-context";
import {
  useFrappeCreateDoc,
  useFrappeGetCall,
  useFrappeGetDocList,
  useFrappeUpdateDoc,
} from "frappe-react-sdk";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { DataTable } from "./components/data-table";

interface FrappeUser {
  name: string;
  [key: string]: any;
}

interface UserFormValues {
  [key: string]: any;
}

export default function UsersPage() {
  const [users, setUsers] = useState<FrappeUser[]>([]);
  const [listFields, setListFields] = useState<string[]>([]);
  const [filterFields, setFilterFields] = useState<string[]>([]);
  const [standardFilterFields, setStandardFilterFields] = useState<string[]>(
    [],
  );
  const { user } = useUser();

  const isSystemAdmin =
    user?.roles?.some(
      (role: any) =>
        role.role === "System Manager" || role.role === "Administrator",
    ) || false;

  const { data: doctypeData } = useFrappeGetCall(
    "frappe.desk.form.load.getdoctype",
    {
      doctype: "User",
      with_parent: 1,
    },
  );

  useEffect(() => {
    if (doctypeData?.docs) {
      const doc = doctypeData?.docs?.find(
        (d: any) => d.doctype === "DocType" && d.name === "User",
      );
      if (doc && doc.fields) {
        const listFieldsResult: string[] = [];
        const filterFieldsResult: string[] = [];
        const standardFilterFieldsResult: string[] = [];

        doc.fields.forEach((field: any) => {
          const fieldType = field.fieldtype;
          if (
            fieldType !== "Section Break" &&
            fieldType !== "Tab Break" &&
            fieldType !== "Column Break" &&
            fieldType !== "HTML" &&
            fieldType !== "Button" &&
            fieldType !== "Table" &&
            fieldType !== "Table MultiSelect" &&
            fieldType !== "Check" &&
            !field.hidden
          ) {
            if (field.in_list_view) {
              listFieldsResult.push(field.fieldname);
            }
            if (field.in_filter) {
              filterFieldsResult.push(field.fieldname);
            }
            if (field.in_standard_filter) {
              standardFilterFieldsResult.push(field.fieldname);
            }
          }
        });

        setListFields(
          listFieldsResult.length > 0 ? listFieldsResult : ["name"],
        );
        setFilterFields(filterFieldsResult);
        setStandardFilterFields(standardFilterFieldsResult);
      }
    }
  }, [doctypeData]);

  const allFields = [...listFields, ...filterFields, ...standardFilterFields];
  const uniqueFields = [...new Set(allFields)];

  console.log("Unique fields for User doctype:", uniqueFields);

  const {
    data: frappeUsers,
    isLoading: isUsersLoading,
    error: usersError,
    mutate: mutateUsers,
  } = useFrappeGetDocList<FrappeUser>("User", {
    fields: uniqueFields.length > 0 ? uniqueFields : ["name"],
    limit: 100,
    orderBy: {
      field: "creation",
      order: "desc",
    },
  });

  const { createDoc, loading: isCreating } = useFrappeCreateDoc();
  const { updateDoc, loading: isUpdating } = useFrappeUpdateDoc();

  useEffect(() => {
    if (frappeUsers && Array.isArray(frappeUsers)) {
      setUsers(frappeUsers);
    }
  }, [frappeUsers]);

  const handleAddUser = async (userData: UserFormValues) => {
    if (!isSystemAdmin) {
      toast.error("Only System Administrators can add users");
      return;
    }

    if (!userData.email) {
      toast.error("Email is required to create a user");
      return;
    }

    try {
      const newUser = {
        ...userData,
        doctype: "User",
        user_type: userData.user_type || "System User",
        send_welcome_email: false,
      };

      await createDoc("User", newUser);
      toast.success("User created successfully");
      mutateUsers();
    } catch (error: any) {
      console.error("Error creating user:", error);
      toast.error(error?.message || "Failed to create user. Please try again.");
    }
  };

  const handleDeleteUser = async (user: FrappeUser) => {
    if (!isSystemAdmin) {
      toast.error("Only System Administrators can delete users");
      return;
    }

    if (user.name === "Administrator") {
      toast.error("Cannot delete the Administrator user");
      return;
    }

    try {
      const response = await fetch("/api/method/frappe.client.delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          doctype: "User",
          name: user.name,
        }),
      });

      const result = await response.json();

      if (result.data) {
        toast.success("User deleted successfully");
        mutateUsers();
      } else {
        throw new Error(result.message || "Failed to delete user");
      }
    } catch (error: any) {
      console.error("Error deleting user:", error);
      toast.error(error?.message || "Failed to delete user. Please try again.");
    }
  };

  const handleEditUser = async (
    user: FrappeUser,
    field: string,
    value: any,
  ) => {
    if (!isSystemAdmin) {
      toast.error("Only System Administrators can edit users");
      return;
    }

    try {
      await updateDoc("User", user.name, {
        [field]: value,
      });
      toast.success("User updated successfully");
      mutateUsers();
    } catch (error: any) {
      console.error("Error updating user:", error);
      toast.error(error?.message || "Failed to update user. Please try again.");
    }
  };

  const handleToggleStatus = async (user: FrappeUser) => {
    if (!isSystemAdmin) {
      toast.error("Only System Administrators can change user status");
      return;
    }

    if (user.name === "Administrator") {
      toast.error("Cannot change Administrator status");
      return;
    }

    await handleEditUser(user, "enabled", user.enabled ? 0 : 1);
  };

  if (usersError) {
    return (
      <BaseLayout
        title="Users"
        description="Manage your users and their permissions"
      >
        <div className="flex flex-col items-center justify-center h-[400px]">
          <p className="text-red-500">
            Error loading users: {(usersError as any)?.message}
          </p>
        </div>
      </BaseLayout>
    );
  }

  return (
    <BaseLayout title="Users" description="Manage users">
      <div className="flex flex-col gap-4">
        <div className="@container/main px-4 lg:px-6 mt-8 lg:mt-12">
          <DataTable
            users={users}
            onDeleteUser={handleDeleteUser}
            onEditUser={handleEditUser}
            onAddUser={handleAddUser}
            onToggleStatus={handleToggleStatus}
            isLoading={isUsersLoading || isCreating || isUpdating}
            isSystemAdmin={isSystemAdmin}
            listFields={listFields}
            filterFields={filterFields}
            standardFilterFields={standardFilterFields}
          />
        </div>
      </div>
    </BaseLayout>
  );
}
